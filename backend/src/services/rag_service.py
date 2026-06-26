# backend/src/services/rag_service.py
"""
Orchestrates the full RAG pipeline — now with hybrid search support.
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import BadRequestError, NotFoundError
from src.core.logging import logger
from src.models.message import MessageRole
from src.models.user import User
from src.rag.citations import build_citations
from src.rag.context_builder import build_context
from src.rag.hybrid_retriever import hybrid_retrieve
from src.rag.llm_service import embed_query_async, generate_answer_async
from src.rag.prompt_templates import build_rag_prompt
from src.rag.reranker import diversify_results
from src.rag.retriever import retrieve_similar_chunks
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.document_repository import DocumentRepository
from src.schemas.rag import ChatRequest, ChatResponse


class RAGService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._convo_repo = ConversationRepository(session)
        self._doc_repo = DocumentRepository(session)

    async def chat(
        self,
        request: ChatRequest,
        current_user: User,
    ) -> ChatResponse:

        # ── Step 0: Validate document ownership ───────────────────────────────
        if request.document_id:
            doc = await self._doc_repo.get_by_id(request.document_id)
            if not doc or (
                doc.user_id != current_user.id and not current_user.is_superuser
            ):
                raise NotFoundError("Document not found.")

        # ── Step 1: Get or create conversation ────────────────────────────────
        if request.conversation_id:
            convo = await self._convo_repo.get_conversation(request.conversation_id)
            if not convo or convo.user_id != current_user.id:
                raise NotFoundError("Conversation not found.")
        else:
            title = request.question[:60] + (
                "..." if len(request.question) > 60 else ""
            )
            convo = await self._convo_repo.create_conversation(
                user_id=current_user.id,
                document_id=request.document_id,
                title=title,
            )

        # ── Step 2: Build conversation history ────────────────────────────────
        recent_messages = await self._convo_repo.get_recent_messages(
            convo.id, limit=6
        )
        history = [
            {"role": msg.role.value, "content": msg.content}
            for msg in recent_messages
        ]

        # ── Step 3: Embed the query ───────────────────────────────────────────
        logger.info(
            "rag.embed_query",
            conversation_id=str(convo.id),
            use_hybrid=request.use_hybrid,
        )
        try:
            query_embedding = await embed_query_async(request.question)
        except RuntimeError as exc:
            raise BadRequestError(f"Failed to embed query: {exc}")

        # ── Step 4: Retrieve chunks ───────────────────────────────────────────
        if request.use_hybrid:
            raw_chunks = await hybrid_retrieve(
                self._session,
                query=request.question,
                query_embedding=query_embedding,
                user_id=current_user.id,
                document_id=request.document_id,
                top_k=request.top_k * 2,   # over-fetch before diversity filter
                vector_weight=request.vector_weight,
                fts_weight=request.fts_weight,
            )
            # Apply diversity filter then trim to top_k
            retrieved_chunks = diversify_results(raw_chunks)[:request.top_k]
            search_mode = "hybrid"
        else:
            retrieved_chunks = await retrieve_similar_chunks(
                self._session,
                query_embedding=query_embedding,
                user_id=current_user.id,
                document_id=request.document_id,
                top_k=request.top_k,
            )
            search_mode = "vector"

        # ── Step 5: Build context ─────────────────────────────────────────────
        context_string, used_chunks = build_context(retrieved_chunks)

        # ── Step 6: Generate answer ───────────────────────────────────────────
        messages = build_rag_prompt(
            question=request.question,
            context=context_string,
            conversation_history=history,
        )

        logger.info(
            "rag.generate",
            conversation_id=str(convo.id),
            search_mode=search_mode,
            context_chunks=len(used_chunks),
        )
        answer = await generate_answer_async(messages)

        # ── Step 7: Persist messages ──────────────────────────────────────────
        await self._convo_repo.add_message(
            conversation_id=convo.id,
            role=MessageRole.USER,
            content=request.question,
            token_count=len(request.question) // 4,
        )

        assistant_msg = await self._convo_repo.add_message(
            conversation_id=convo.id,
            role=MessageRole.ASSISTANT,
            content=answer,
            token_count=len(answer) // 4,
        )

        # ── Step 8: Persist citations ─────────────────────────────────────────
        if used_chunks:
            await self._convo_repo.add_citations(
                assistant_msg.id,
                [
                    {
                        "chunk_id": chunk.chunk_id,
                        "relevance_score": chunk.similarity_score,
                        "citation_index": i,
                    }
                    for i, chunk in enumerate(used_chunks)
                ],
            )

        await self._session.commit()

        # ── Step 9: Build response ────────────────────────────────────────────
        citations = build_citations(used_chunks, assistant_msg.id)

        logger.info(
            "rag.complete",
            conversation_id=str(convo.id),
            search_mode=search_mode,
            citations=len(citations),
        )

        return ChatResponse(
            answer=answer,
            conversation_id=convo.id,
            message_id=assistant_msg.id,
            citations=citations,
            model=settings.ollama_chat_model,
            retrieved_chunks=len(retrieved_chunks),
            search_mode=search_mode,
        )
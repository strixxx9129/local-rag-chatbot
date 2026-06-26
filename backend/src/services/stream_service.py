# backend/src/services/stream_service.py
"""
Streaming RAG pipeline.

Runs the same pipeline as RAGService but streams the LLM answer
token-by-token via Server-Sent Events.

SSE event format (NDJSON over text/event-stream):
  data: {"type": "status",   "content": "Searching documents..."}
  data: {"type": "token",    "content": "The "}
  data: {"type": "token",    "content": "answer "}
  data: {"type": "token",    "content": "is..."}
  data: {"type": "metadata", "content": {...citations, conversation_id...}}
  data: {"type": "done"}
  data: {"type": "error",    "content": "Error message"}

Why structured events instead of raw tokens?
  The client needs to distinguish token content from metadata (citations,
  conversation_id, message_id). Structured events let the frontend
  update the citation panel in real-time after the stream completes
  without a second HTTP round-trip.
"""
import json
import uuid
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import BadRequestError, NotFoundError
from src.core.logging import logger
from src.models.message import MessageRole
from src.models.user import User
from src.rag.citations import build_citations
from src.rag.context_builder import build_context
from src.rag.hybrid_retriever import hybrid_retrieve
from src.rag.llm_service import embed_query_async, stream_answer_async
from src.rag.prompt_templates import build_rag_prompt
from src.rag.reranker import diversify_results
from src.rag.retriever import retrieve_similar_chunks
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.document_repository import DocumentRepository
from src.schemas.rag import ChatRequest


def _sse_event(event_type: str, content) -> str:
    """
    Format a single SSE data line.

    SSE protocol requires lines prefixed with 'data: ' and
    terminated with double newline.
    """
    payload = json.dumps({"type": event_type, "content": content})
    return f"data: {payload}\n\n"


class StreamService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._convo_repo = ConversationRepository(session)
        self._doc_repo = DocumentRepository(session)

    async def stream_chat(
        self,
        request: ChatRequest,
        current_user: User,
    ) -> AsyncGenerator[str, None]:
        """
        Execute the RAG pipeline and stream the LLM answer as SSE events.

        Yields SSE-formatted strings. FastAPI's StreamingResponse consumes
        this generator and sends each chunk to the client immediately.
        """

        # ── Step 0: Validate document ─────────────────────────────────────────
        if request.document_id:
            doc = await self._doc_repo.get_by_id(request.document_id)
            if not doc or (
                doc.user_id != current_user.id
                and not current_user.is_superuser
            ):
                yield _sse_event("error", "Document not found.")
                return

        # ── Step 1: Get or create conversation ────────────────────────────────
        yield _sse_event("status", "Starting conversation...")

        try:
            if request.conversation_id:
                convo = await self._convo_repo.get_conversation(
                    request.conversation_id
                )
                if not convo or convo.user_id != current_user.id:
                    yield _sse_event("error", "Conversation not found.")
                    return
            else:
                title = request.question[:60] + (
                    "..." if len(request.question) > 60 else ""
                )
                convo = await self._convo_repo.create_conversation(
                    user_id=current_user.id,
                    document_id=request.document_id,
                    title=title,
                )
                await self._session.commit()
        except Exception as exc:
            logger.exception("stream_service.conversation_failed", error=str(exc))
            yield _sse_event("error", "Failed to initialize conversation.")
            return

        # ── Step 2: Load conversation history ─────────────────────────────────
        recent_messages = await self._convo_repo.get_recent_messages(
            convo.id, limit=6
        )
        history = [
            {"role": msg.role.value, "content": msg.content}
            for msg in recent_messages
        ]

        # ── Step 3: Embed query ───────────────────────────────────────────────
        yield _sse_event("status", "Embedding query...")

        try:
            query_embedding = await embed_query_async(request.question)
        except Exception as exc:
            logger.exception("stream_service.embed_failed", error=str(exc))
            yield _sse_event("error", f"Failed to embed query: {exc}")
            return

        # ── Step 4: Retrieve chunks ───────────────────────────────────────────
        yield _sse_event("status", "Searching documents...")

        try:
            if request.use_hybrid:
                raw_chunks = await hybrid_retrieve(
                    self._session,
                    query=request.question,
                    query_embedding=query_embedding,
                    user_id=current_user.id,
                    document_id=request.document_id,
                    top_k=request.top_k * 2,
                    vector_weight=request.vector_weight,
                    fts_weight=request.fts_weight,
                )
                retrieved_chunks = diversify_results(raw_chunks)[: request.top_k]
            else:
                retrieved_chunks = await retrieve_similar_chunks(
                    self._session,
                    query_embedding=query_embedding,
                    user_id=current_user.id,
                    document_id=request.document_id,
                    top_k=request.top_k,
                )
        except Exception as exc:
            logger.exception("stream_service.retrieve_failed", error=str(exc))
            yield _sse_event("error", f"Retrieval failed: {exc}")
            return

        # ── Step 5: Build context ─────────────────────────────────────────────
        yield _sse_event(
            "status",
            f"Found {len(retrieved_chunks)} relevant chunks. Generating answer...",
        )

        context_string, used_chunks = build_context(retrieved_chunks)

        # ── Step 6: Build prompt ──────────────────────────────────────────────
        messages = build_rag_prompt(
            question=request.question,
            context=context_string,
            conversation_history=history,
        )

        # ── Step 7: Persist user message ──────────────────────────────────────
        try:
            await self._convo_repo.add_message(
                conversation_id=convo.id,
                role=MessageRole.USER,
                content=request.question,
                token_count=len(request.question) // 4,
            )
            await self._session.commit()
        except Exception as exc:
            logger.warning("stream_service.user_msg_failed", error=str(exc))

        # ── Step 8: Stream tokens ─────────────────────────────────────────────
        full_answer = ""

        try:
            async for token in stream_answer_async(messages):
                full_answer += token
                yield _sse_event("token", token)

        except Exception as exc:
            logger.exception("stream_service.stream_failed", error=str(exc))
            yield _sse_event("error", f"Streaming failed: {exc}")
            return

        # ── Step 9: Persist assistant message + citations ─────────────────────
        try:
            assistant_msg = await self._convo_repo.add_message(
                conversation_id=convo.id,
                role=MessageRole.ASSISTANT,
                content=full_answer,
                token_count=len(full_answer) // 4,
            )

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
            message_id = str(assistant_msg.id)

        except Exception as exc:
            logger.warning("stream_service.persist_failed", error=str(exc))
            message_id = str(uuid.uuid4())

        # ── Step 10: Send metadata event ──────────────────────────────────────
        citations = build_citations(used_chunks, uuid.UUID(message_id))
        citation_dicts = [
            {
                "chunk_id": str(c.chunk_id),
                "document_id": str(c.document_id),
                "document_title": c.document_title,
                "page_number": c.page_number,
                "content_snippet": c.content_snippet,
                "relevance_score": c.relevance_score,
            }
            for c in citations
        ]

        metadata = {
            "conversation_id": str(convo.id),
            "message_id": message_id,
            "citations": citation_dicts,
            "model": settings.ollama_chat_model,
            "retrieved_chunks": len(retrieved_chunks),
            "search_mode": "hybrid" if request.use_hybrid else "vector",
        }

        yield _sse_event("metadata", metadata)

        # ── Step 11: Signal completion ────────────────────────────────────────
        yield _sse_event("done", "")

        # ── Step 12: Enqueue background memory summarization ──────────────────
        try:
            from src.workers.memory_worker import summarize_conversation
            from src.workers.queue import memory_queue

            memory_queue.enqueue(
                summarize_conversation,
                args=(str(convo.id),),
                job_id=f"mem-{convo.id}-{message_id[:8]}",
            )
        except Exception as exc:
            logger.warning(
                "stream_service.memory_enqueue_failed", error=str(exc)
            )

        logger.info(
            "stream_service.complete",
            conversation_id=str(convo.id),
            tokens=len(full_answer),
            citations=len(citation_dicts),
        )
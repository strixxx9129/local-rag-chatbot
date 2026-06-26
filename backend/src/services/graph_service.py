# backend/src/services/graph_service.py
"""
Graph service — the bridge between FastAPI and the LangGraph agent.

Builds a session-bound LangGraph per request and maps the
final state to a ChatResponse.
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import BadRequestError
from src.core.logging import logger
from src.graph.builder import build_rag_graph_with_session
from src.graph.state import GraphState
from src.models.user import User
from src.schemas.rag import ChatRequest, ChatResponse, CitationResponse


class GraphService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def chat(
        self,
        request: ChatRequest,
        current_user: User,
    ) -> ChatResponse:
        """
        Execute the LangGraph RAG agent for one chat turn.
        """

        # ── Build initial state ───────────────────────────────────────────────
        initial_state: GraphState = {
            # Input
            "question": request.question,
            "user_id": str(current_user.id),
            "document_id": (
                str(request.document_id) if request.document_id else None
            ),
            "conversation_id": (
                str(request.conversation_id)
                if request.conversation_id
                else None
            ),
            "top_k": request.top_k,
            "use_hybrid": request.use_hybrid,
            "vector_weight": request.vector_weight,
            "fts_weight": request.fts_weight,
            # Query analysis — populated by query_analyzer_node
            "query_type": "",
            "standalone_question": "",
            "needs_retrieval": True,
            # Memory — populated by memory_node
            "long_term_memories": [],
            "memory_context": "",
            "query_embedding": [],
            # Retrieval — populated by retriever_node
            "retrieved_chunks": [],
            "retrieval_mode": "none",
            # Context — populated by context_builder_node
            "context_string": "",
            "used_chunks": [],
            # Generation — populated by generator_node
            "answer": "",
            "prompt_messages": [],
            # Citations — populated by citation_builder_node
            "citations": [],
            # Conversation — populated by query_analyzer_node + generator_node
            "conversation_history": [],
            "resolved_conversation_id": "",
            "resolved_message_id": "",
            # Error — set by any node on failure
            "error": None,
        }

        # ── Build session-bound graph ─────────────────────────────────────────
        graph = build_rag_graph_with_session(self._session)

        logger.info(
            "graph_service.invoke",
            user_id=str(current_user.id),
            question=request.question[:80],
        )

        # ── Execute ───────────────────────────────────────────────────────────
        try:
            final_state: GraphState = await graph.ainvoke(initial_state)
        except Exception as exc:
            logger.exception("graph_service.invoke_failed", error=str(exc))
            raise BadRequestError(f"Agent execution failed: {exc}")

        if final_state.get("error"):
            logger.warning(
                "graph_service.state_error",
                error=final_state["error"],
            )

        # ── Map state → ChatResponse ──────────────────────────────────────────
        citations = [
            CitationResponse(
                chunk_id=uuid.UUID(c["chunk_id"]),
                document_id=uuid.UUID(c["document_id"]),
                document_title=c["document_title"],
                page_number=c.get("page_number"),
                content_snippet=c["content_snippet"],
                relevance_score=c["relevance_score"],
            )
            for c in final_state.get("citations", [])
        ]

        answer = final_state.get("answer") or (
            "I was unable to generate a response. Please try again."
        )

        # resolved_conversation_id must always be set by query_analyzer_node
        raw_convo_id = final_state.get("resolved_conversation_id")
        if not raw_convo_id:
            raise BadRequestError("Graph failed to resolve conversation ID.")

        raw_msg_id = final_state.get("resolved_message_id") or str(uuid.uuid4())

        return ChatResponse(
            answer=answer,
            conversation_id=uuid.UUID(raw_convo_id),
            message_id=uuid.UUID(raw_msg_id),
            citations=citations,
            model=settings.ollama_chat_model,
            retrieved_chunks=len(final_state.get("retrieved_chunks", [])),
            search_mode=final_state.get("retrieval_mode", "none"),
        )

# backend/src/graph/nodes/memory.py
"""
Memory node — retrieves relevant long-term memories before generation.

Position in the graph:
  query_analyzer → [memory_node] → retriever → context_builder → generator

Why before retrieval?
  The memory context might clarify a vague follow-up question before
  we embed it for vector search. It also feeds into the generator
  alongside document chunks.

Reads:  standalone_question, user_id, resolved_conversation_id,
        (query embedding computed here)
Writes: long_term_memories, memory_context
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import logger
from src.graph.state import GraphState
from src.rag.llm_service import embed_query_async
from src.services.memory_service import MemoryService

MEMORY_TOKEN_BUDGET = 800       # chars reserved for memory context
CHARS_PER_TOKEN = 4
MEMORY_CHAR_BUDGET = MEMORY_TOKEN_BUDGET * CHARS_PER_TOKEN


def _format_memory_context(memories: list[dict]) -> str:
    """
    Format retrieved memories into a prompt-ready string.

    Each memory is prefixed with its source conversation window
    so the LLM knows this is prior context, not current context.
    """
    if not memories:
        return ""

    parts = []
    chars_used = 0

    for i, memory in enumerate(memories):
        block = (
            f"[Past Context {i + 1}] "
            f"(Conversation window: {memory['message_window']})\n"
            f"{memory['summary']}"
        )
        if chars_used + len(block) > MEMORY_CHAR_BUDGET:
            break
        parts.append(block)
        chars_used += len(block)

    return "\n\n".join(parts)


async def memory_node(
    state: GraphState,
    *,
    session: AsyncSession,
) -> GraphState:
    """
    LangGraph node: retrieve long-term memories relevant to the query.
    """
    question = state.get("standalone_question") or state["question"]
    user_id = uuid.UUID(state["user_id"])
    convo_id_str = state.get("resolved_conversation_id")

    current_convo_id = (
        uuid.UUID(convo_id_str) if convo_id_str else None
    )

    logger.info(
        "node.memory.start",
        question=question[:80],
        user_id=str(user_id),
    )

    try:
        # Embed the query (reuse from retriever if available later,
        # but memory runs before retriever so we embed here)
        query_embedding = await embed_query_async(question)

        service = MemoryService(session)
        memories = await service.retrieve_memories(
            query=question,
            query_embedding=query_embedding,
            user_id=user_id,
            current_conversation_id=current_convo_id,
            top_k=3,
        )

        memory_context = _format_memory_context(memories)

        logger.info(
            "node.memory.complete",
            memories_found=len(memories),
            context_chars=len(memory_context),
        )

        return {
            **state,
            "long_term_memories": memories,
            "memory_context": memory_context,
            "query_embedding": query_embedding,
        }

    except Exception as exc:
        # Memory failure is non-fatal — degrade gracefully
        logger.warning("node.memory.failed", error=str(exc))
        return {
            **state,
            "long_term_memories": [],
            "memory_context": "",
            "query_embedding": [],
        }

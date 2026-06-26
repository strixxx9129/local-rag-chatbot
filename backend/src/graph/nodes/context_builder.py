# backend/src/graph/nodes/context_builder.py
"""
Context builder node — assembles retrieved chunks into a prompt-ready
context string within the token budget.

Reads:  retrieved_chunks (list of dicts)
Writes: context_string, used_chunks (list of dicts)
"""
from src.core.logging import logger
from src.graph.state import GraphState
from src.rag.context_builder import build_context
from src.schemas.rag import RetrievedChunk
import uuid


def _dict_to_chunk(d: dict) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.UUID(d["chunk_id"]),
        document_id=uuid.UUID(d["document_id"]),
        document_title=d["document_title"],
        content=d["content"],
        page_number=d.get("page_number"),
        chunk_index=d["chunk_index"],
        similarity_score=d["similarity_score"],
    )


async def context_builder_node(state: GraphState) -> GraphState:
    """
    LangGraph node: build token-budgeted context from retrieved chunks.
    """
    raw_chunks = state.get("retrieved_chunks", [])

    logger.info(
        "node.context_builder.start",
        input_chunks=len(raw_chunks),
    )

    if not raw_chunks:
        return {
            **state,
            "context_string": "",
            "used_chunks": [],
        }

    chunks = [_dict_to_chunk(d) for d in raw_chunks]
    context_string, used_chunks = build_context(chunks)

    used_dicts = [
        {
            "chunk_id": str(c.chunk_id),
            "document_id": str(c.document_id),
            "document_title": c.document_title,
            "content": c.content,
            "page_number": c.page_number,
            "chunk_index": c.chunk_index,
            "similarity_score": c.similarity_score,
        }
        for c in used_chunks
    ]

    logger.info(
        "node.context_builder.complete",
        used_chunks=len(used_dicts),
        context_chars=len(context_string),
    )

    return {
        **state,
        "context_string": context_string,
        "used_chunks": used_dicts,
    }
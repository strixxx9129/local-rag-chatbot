# backend/src/graph/nodes/citation_builder.py
"""
Citation builder node — converts used_chunks into CitationResponse dicts
and persists them to the message_citations table.

Reads:  used_chunks, resolved_message_id
Writes: citations (list of dicts)
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import logger
from src.graph.state import GraphState
from src.rag.citations import build_citations
from src.repositories.conversation_repository import ConversationRepository
from src.schemas.rag import RetrievedChunk


async def citation_builder_node(
    state: GraphState,
    *,
    session: AsyncSession,
) -> GraphState:
    """
    LangGraph node: build and persist citations for the assistant message.
    """
    used_chunks_dicts = state.get("used_chunks", [])
    message_id_str = state.get("resolved_message_id")

    if not used_chunks_dicts or not message_id_str:
        return {**state, "citations": []}

    message_id = uuid.UUID(message_id_str)

    # Reconstruct RetrievedChunk objects
    used_chunks = [
        RetrievedChunk(
            chunk_id=uuid.UUID(d["chunk_id"]),
            document_id=uuid.UUID(d["document_id"]),
            document_title=d["document_title"],
            content=d["content"],
            page_number=d.get("page_number"),
            chunk_index=d["chunk_index"],
            similarity_score=d["similarity_score"],
        )
        for d in used_chunks_dicts
    ]

    # Persist to DB
    repo = ConversationRepository(session)
    try:
        await repo.add_citations(
            message_id,
            [
                {
                    "chunk_id": chunk.chunk_id,
                    "relevance_score": chunk.similarity_score,
                    "citation_index": i,
                }
                for i, chunk in enumerate(used_chunks)
            ],
        )
        await session.commit()
    except Exception as exc:
        logger.warning("node.citation_builder.persist_failed", error=str(exc))

    # Build response objects
    citation_objects = build_citations(used_chunks, message_id)
    citation_dicts = [
        {
            "chunk_id": str(c.chunk_id),
            "document_id": str(c.document_id),
            "document_title": c.document_title,
            "page_number": c.page_number,
            "content_snippet": c.content_snippet,
            "relevance_score": c.relevance_score,
        }
        for c in citation_objects
    ]

    logger.info(
        "node.citation_builder.complete",
        citations=len(citation_dicts),
    )

    return {**state, "citations": citation_dicts}
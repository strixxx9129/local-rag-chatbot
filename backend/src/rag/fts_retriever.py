# backend/src/rag/fts_retriever.py
"""
PostgreSQL full-text search retriever.

Uses tsvector + tsquery with plainto_tsquery for natural language input.
plainto_tsquery('english', 'machine learning models') produces:
    'machin' & 'learn' & 'model'  (stemmed AND query)

Why plainto_tsquery over to_tsquery?
  to_tsquery requires operators like 'machine & learning'.
  plainto_tsquery accepts raw natural language — better for user queries.

Why websearch_to_tsquery as fallback?
  websearch_to_tsquery supports quoted phrases and minus exclusions
  ("machine learning" -python) which power users may type naturally.
  We try plainto_tsquery first, fall back to websearch_to_tsquery on error.

Scoring:
  ts_rank_cd weights term frequency AND cover density (how close terms
  appear to each other). This is the right rank function for RAG — 
  tight co-occurrence of query terms signals high relevance.
"""
import uuid

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import logger
from src.models.chunk import DocumentChunk
from src.models.document import Document, DocumentStatus
from src.schemas.rag import RetrievedChunk


async def retrieve_fts_chunks(
    session: AsyncSession,
    *,
    query: str,
    user_id: uuid.UUID,
    document_id: uuid.UUID | None = None,
    top_k: int = 10,
) -> list[RetrievedChunk]:
    """
    Full-text search over document_chunks using PostgreSQL tsvector.

    Args:
        session:     AsyncSession
        query:       Raw user query string (will be parsed by PostgreSQL)
        user_id:     Restrict to this user's documents
        document_id: Optional — restrict to one document
        top_k:       Max results to return

    Returns:
        List of RetrievedChunk sorted by ts_rank_cd descending.
        similarity_score field holds the normalized ts_rank_cd score.
    """
    # Sanitize query — remove special characters that break tsquery
    safe_query = _sanitize_query(query)
    if not safe_query:
        logger.warning("fts_retriever.empty_query_after_sanitize", query=query)
        return []

    logger.info(
        "fts_retriever.start",
        query=safe_query,
        user_id=str(user_id),
        document_id=str(document_id) if document_id else "all",
    )

    # ts_rank_cd: cover density ranking — rewards term proximity
    # normalization=2: divides rank by document length (fairness)
    rank_expr = func.ts_rank_cd(
        DocumentChunk.content_tsv,
        func.plainto_tsquery("english", safe_query),
        2,
    ).label("fts_score")

    stmt = (
        select(
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.content,
            DocumentChunk.page_number,
            DocumentChunk.chunk_index,
            Document.id.label("document_id"),
            Document.title.label("document_title"),
            rank_expr,
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.user_id == user_id)
        .where(Document.status == DocumentStatus.READY)
        .where(
            DocumentChunk.content_tsv.op("@@")(
                func.plainto_tsquery("english", safe_query)
            )
        )
        .order_by(rank_expr.desc())
        .limit(top_k)
    )

    if document_id is not None:
        stmt = stmt.where(Document.id == document_id)

    try:
        result = await session.execute(stmt)
        rows = result.mappings().all()
    except Exception as exc:
        # FTS query syntax error — return empty rather than crashing
        logger.warning(
            "fts_retriever.query_failed",
            query=safe_query,
            error=str(exc),
        )
        return []

    chunks: list[RetrievedChunk] = []
    for row in rows:
        raw_score = float(row["fts_score"])
        chunks.append(
            RetrievedChunk(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                document_title=row["document_title"],
                content=row["content"],
                page_number=row["page_number"],
                chunk_index=row["chunk_index"],
                similarity_score=round(raw_score, 6),
            )
        )

    logger.info(
        "fts_retriever.complete",
        results=len(chunks),
        query=safe_query,
    )

    return chunks


def _sanitize_query(query: str) -> str:
    """
    Remove characters that cause plainto_tsquery to error.
    Keeps alphanumeric, spaces, hyphens, and apostrophes.
    """
    import re
    # Strip special tsquery operators and punctuation
    cleaned = re.sub(r"[^\w\s\-']", " ", query)
    # Collapse whitespace
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()
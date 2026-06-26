# backend/src/rag/retriever.py
"""
Vector similarity retriever using pgvector.

Queries the embeddings table using cosine distance (<=>),
joins to chunks and documents to return enriched results.

Two retrieval modes:
  - Document-scoped: search within a single document
  - User-scoped:     search across all documents owned by the user

The similarity score is converted from cosine DISTANCE to cosine
SIMILARITY: similarity = 1 - distance, so 1.0 = identical, 0.0 = orthogonal.
"""
import uuid
from typing import Sequence

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logging import logger
from src.models.chunk import DocumentChunk
from src.models.document import Document, DocumentStatus
from src.models.embedding import Embedding
from src.schemas.rag import RetrievedChunk


async def retrieve_similar_chunks(
    session: AsyncSession,
    *,
    query_embedding: list[float],
    user_id: uuid.UUID,
    document_id: uuid.UUID | None = None,
    top_k: int = 5,
    similarity_threshold: float = 0.3,
) -> list[RetrievedChunk]:
    """
    Find the top-K most semantically similar chunks to the query embedding.

    Args:
        session:              AsyncSession (from FastAPI dependency)
        query_embedding:      Float vector from Ollama embed call
        user_id:              Restrict search to this user's documents
        document_id:          Optional — restrict to one document
        top_k:                How many chunks to return
        similarity_threshold: Filter out chunks below this similarity score

    Returns:
        List of RetrievedChunk sorted by similarity descending.
    """
    # Build the pgvector cosine distance expression
    # Cast the Python list to a PostgreSQL vector literal
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    # Cosine DISTANCE (lower = more similar, range 0–2)
    # We select (1 - distance) as similarity for human-readable scoring
    query = (
        select(
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.content,
            DocumentChunk.page_number,
            DocumentChunk.chunk_index,
            Document.id.label("document_id"),
            Document.title.label("document_title"),
            (
                1 - Embedding.embedding.cosine_distance(
                    text(f"'{embedding_str}'::vector")
                )
            ).label("similarity_score"),
        )
        .join(Embedding, Embedding.chunk_id == DocumentChunk.id)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.user_id == user_id)
        .where(Document.status == DocumentStatus.READY)
        .order_by(
            Embedding.embedding.cosine_distance(
                text(f"'{embedding_str}'::vector")
            )
        )
        .limit(top_k * 2)   # over-fetch then filter by threshold
    )

    if document_id is not None:
        query = query.where(Document.id == document_id)

    result = await session.execute(query)
    rows = result.mappings().all()

    chunks: list[RetrievedChunk] = []
    for row in rows:
        score = float(row["similarity_score"])
        if score < similarity_threshold:
            continue
        chunks.append(
            RetrievedChunk(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                document_title=row["document_title"],
                content=row["content"],
                page_number=row["page_number"],
                chunk_index=row["chunk_index"],
                similarity_score=round(score, 4),
            )
        )

    # Trim to top_k after threshold filtering
    chunks = chunks[:top_k]

    logger.info(
        "retriever.complete",
        user_id=str(user_id),
        document_id=str(document_id) if document_id else "all",
        top_k=top_k,
        retrieved=len(chunks),
    )

    return chunks
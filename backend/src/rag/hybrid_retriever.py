# backend/src/rag/hybrid_retriever.py
"""
Hybrid retrieval: vector search + full-text search fused with RRF.

Reciprocal Rank Fusion (RRF):
  For each result list, assign a score: 1 / (k + rank)
  where k=60 (standard constant — softens the impact of top ranks).
  Sum RRF scores across lists for documents appearing in multiple lists.
  Sort by combined RRF score descending.

Why k=60?
  Empirically found optimal in the original RRF paper (Cormack et al. 2009).
  It ensures rank 1 doesn't completely dominate over ranks 2-5.

Example:
  Chunk A: rank 1 in vector → 1/61 = 0.0164
            rank 3 in FTS   → 1/63 = 0.0159
            combined        → 0.0323  ← likely winner

  Chunk B: rank 1 in FTS only → 1/61 = 0.0164
            not in vector results
            combined        → 0.0164

Result: Chunk A wins because it appeared in both lists.
        Cross-list reinforcement is the core insight of RRF.
"""
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import logger
from src.rag.fts_retriever import retrieve_fts_chunks
from src.rag.retriever import retrieve_similar_chunks
from src.schemas.rag import RetrievedChunk

RRF_K = 60          # Standard RRF constant
DEFAULT_TOP_K = 10  # Over-fetch before final trim


@dataclass
class RRFResult:
    chunk: RetrievedChunk
    rrf_score: float = 0.0
    in_vector: bool = False
    in_fts: bool = False
    vector_rank: int | None = None
    fts_rank: int | None = None


async def hybrid_retrieve(
    session: AsyncSession,
    *,
    query: str,
    query_embedding: list[float],
    user_id: uuid.UUID,
    document_id: uuid.UUID | None = None,
    top_k: int = 5,
    vector_weight: float = 0.6,
    fts_weight: float = 0.4,
    fetch_k: int = 20,
) -> list[RetrievedChunk]:
    """
    Run vector search and FTS in parallel, fuse with weighted RRF.

    Args:
        session:          AsyncSession
        query:            Raw user query string (for FTS)
        query_embedding:  Pre-computed query vector (for vector search)
        user_id:          Restrict to user's documents
        document_id:      Optional document scope
        top_k:            Final number of results to return
        vector_weight:    RRF weight for vector results (default 0.6)
        fts_weight:       RRF weight for FTS results (default 0.4)
        fetch_k:          How many results to fetch from each source
                          before fusion (over-fetch for better recall)

    Returns:
        Top-K chunks ranked by combined RRF score.
    """
    import asyncio

    # ── Run both retrievers concurrently ──────────────────────────────────────
    vector_task = retrieve_similar_chunks(
        session,
        query_embedding=query_embedding,
        user_id=user_id,
        document_id=document_id,
        top_k=fetch_k,
        similarity_threshold=0.1,   # lower threshold — RRF handles reranking
    )
    fts_task = retrieve_fts_chunks(
        session,
        query=query,
        user_id=user_id,
        document_id=document_id,
        top_k=fetch_k,
    )

    vector_results, fts_results = await asyncio.gather(vector_task, fts_task)

    logger.info(
        "hybrid_retriever.sources",
        vector_count=len(vector_results),
        fts_count=len(fts_results),
    )

    # ── Build RRF score map keyed by chunk_id ─────────────────────────────────
    rrf_map: dict[uuid.UUID, RRFResult] = {}

    # Process vector results
    for rank, chunk in enumerate(vector_results, start=1):
        rrf_score = vector_weight * (1.0 / (RRF_K + rank))
        if chunk.chunk_id not in rrf_map:
            rrf_map[chunk.chunk_id] = RRFResult(chunk=chunk)
        rrf_map[chunk.chunk_id].rrf_score += rrf_score
        rrf_map[chunk.chunk_id].in_vector = True
        rrf_map[chunk.chunk_id].vector_rank = rank

    # Process FTS results
    for rank, chunk in enumerate(fts_results, start=1):
        rrf_score = fts_weight * (1.0 / (RRF_K + rank))
        if chunk.chunk_id not in rrf_map:
            rrf_map[chunk.chunk_id] = RRFResult(chunk=chunk)
        rrf_map[chunk.chunk_id].rrf_score += rrf_score
        rrf_map[chunk.chunk_id].in_fts = True
        rrf_map[chunk.chunk_id].fts_rank = rank

    # ── Sort by RRF score descending ──────────────────────────────────────────
    ranked = sorted(rrf_map.values(), key=lambda r: r.rrf_score, reverse=True)

    # ── Build final result list ───────────────────────────────────────────────
    results: list[RetrievedChunk] = []
    for rrf_result in ranked[:top_k]:
        # Overwrite similarity_score with the RRF score for transparency
        chunk = rrf_result.chunk
        chunk.similarity_score = round(rrf_result.rrf_score, 6)
        results.append(chunk)

    # ── Log fusion stats ──────────────────────────────────────────────────────
    both_count = sum(1 for r in ranked[:top_k] if r.in_vector and r.in_fts)
    vector_only = sum(1 for r in ranked[:top_k] if r.in_vector and not r.in_fts)
    fts_only = sum(1 for r in ranked[:top_k] if r.in_fts and not r.in_vector)

    logger.info(
        "hybrid_retriever.fusion_complete",
        top_k=top_k,
        in_both=both_count,
        vector_only=vector_only,
        fts_only=fts_only,
    )

    return results
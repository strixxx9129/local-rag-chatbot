# backend/src/rag/reranker.py
"""
Post-fusion diversity filter.

Problem: RRF may return 5 consecutive chunks from the same page of the
same document. The context becomes repetitive and the LLM produces a
narrow answer even though other documents have relevant content.

Solution: Maximal Marginal Relevance (MMR)-inspired diversity filter.
  - Accept the top-ranked chunk always.
  - For each subsequent candidate, skip it if a chunk from the same
    document already appears in the accepted list and the candidate's
    rank is beyond a configured diversity window.

This is a lightweight heuristic (not full MMR which requires vector
similarity between candidate chunks). It reliably breaks up same-document
clustering in the top results.
"""
import uuid

from src.core.logging import logger
from src.schemas.rag import RetrievedChunk


def diversify_results(
    chunks: list[RetrievedChunk],
    *,
    max_per_document: int = 3,
) -> list[RetrievedChunk]:
    """
    Filter results to ensure no single document dominates.

    Args:
        chunks:           RRF-ranked chunks (sorted by score descending)
        max_per_document: Max chunks allowed from any single document

    Returns:
        Filtered list — same relative order, same max length.
    """
    if not chunks:
        return []

    doc_counts: dict[uuid.UUID, int] = {}
    accepted: list[RetrievedChunk] = []
    skipped = 0

    for chunk in chunks:
        count = doc_counts.get(chunk.document_id, 0)
        if count >= max_per_document:
            skipped += 1
            continue
        accepted.append(chunk)
        doc_counts[chunk.document_id] = count + 1

    logger.info(
        "reranker.diversify",
        input_count=len(chunks),
        output_count=len(accepted),
        skipped=skipped,
        max_per_document=max_per_document,
    )

    return accepted
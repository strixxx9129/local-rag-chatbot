# backend/src/rag/citations.py
"""
Build citation objects from retrieved chunks.

Citations are grounded in the actual retrieved chunks — not LLM output.
This guarantees every citation is a real source with a real page number
and real content snippet, regardless of what the LLM says.

The citation_index maps to [Source N] references in the LLM answer:
  [Source 1] → citations[0]
  [Source 2] → citations[1]
  etc.
"""
import uuid

from src.schemas.rag import CitationResponse, RetrievedChunk

SNIPPET_LENGTH = 200  # characters to include in the content preview


def build_citations(
    used_chunks: list[RetrievedChunk],
    message_id: uuid.UUID,
) -> list[CitationResponse]:
    """
    Convert retrieved chunks into CitationResponse objects.

    Args:
        used_chunks: Chunks that were included in the LLM context
                     (already filtered to those within token budget)
        message_id:  The assistant message these citations belong to

    Returns:
        List of CitationResponse in the same order as [Source N] references.
    """
    citations: list[CitationResponse] = []

    for chunk in used_chunks:
        # Truncate content to snippet length for the response
        snippet = chunk.content[:SNIPPET_LENGTH]
        if len(chunk.content) > SNIPPET_LENGTH:
            snippet += "..."

        citation = CitationResponse(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            page_number=chunk.page_number,
            content_snippet=snippet,
            relevance_score=chunk.similarity_score,
        )
        citations.append(citation)

    return citations
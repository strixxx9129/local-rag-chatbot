# backend/src/rag/context_builder.py
"""
Assembles retrieved chunks into a context string for the LLM prompt.

Token budget strategy:
  llama3:8b has an 8192 token context window.
  We reserve:
    - 1000 tokens for the system prompt + question
    - 1000 tokens for the LLM's response
    - Remaining ~6000 tokens for retrieved context

  We approximate tokens as len(text) // 4 (4 chars ≈ 1 token).
  This avoids importing tiktoken as a hard dependency while staying
  safely within the context window.

  Chunks are added in similarity order (highest first) until the
  budget is exhausted.
"""
from src.core.logging import logger
from src.schemas.rag import RetrievedChunk

# Token budget constants
CONTEXT_TOKEN_BUDGET = 6000
CHARS_PER_TOKEN = 4
CHAR_BUDGET = CONTEXT_TOKEN_BUDGET * CHARS_PER_TOKEN


def build_context(chunks: list[RetrievedChunk]) -> tuple[str, list[RetrievedChunk]]:
    """
    Build a context string from retrieved chunks within the token budget.

    Returns:
        (context_string, used_chunks)

        context_string: formatted text block to inject into the prompt
        used_chunks:    subset of chunks that fit in the budget
                        (used for citation generation)
    """
    if not chunks:
        return "", []

    used_chunks: list[RetrievedChunk] = []
    context_parts: list[str] = []
    chars_used = 0

    for i, chunk in enumerate(chunks):
        # Format each chunk with source metadata
        header = (
            f"[Source {i + 1}] "
            f"{chunk.document_title}"
            + (f", Page {chunk.page_number}" if chunk.page_number else "")
        )
        block = f"{header}\n{chunk.content}"
        block_chars = len(block)

        if chars_used + block_chars > CHAR_BUDGET:
            logger.debug(
                "context_builder.budget_reached",
                chunks_included=len(used_chunks),
                chunks_skipped=len(chunks) - len(used_chunks),
                chars_used=chars_used,
            )
            break

        context_parts.append(block)
        used_chunks.append(chunk)
        chars_used += block_chars

    context_string = "\n\n---\n\n".join(context_parts)

    logger.info(
        "context_builder.complete",
        total_chunks=len(chunks),
        used_chunks=len(used_chunks),
        estimated_tokens=chars_used // CHARS_PER_TOKEN,
    )

    return context_string, used_chunks
# backend/src/rag/embedder.py
"""
Generate embeddings via Ollama using nomic-embed-text.

Why batch processing?
  Sending 200 chunks as 200 individual HTTP calls to Ollama is slow.
  We process in configurable batches (default 32) — a good balance
  between memory usage and throughput on local hardware.

Why synchronous here?
  This runs inside an RQ worker (a regular Python process, not async).
  The RQ worker calls this synchronously. Ollama's Python client
  is also synchronous. If you later move to an async worker (ARQ),
  swap to httpx.AsyncClient calls against the Ollama REST API.
"""
import time

import ollama

from src.core.config import settings
from src.core.logging import logger
from src.rag.chunker import TextChunk


def embed_chunks(
    chunks: list[TextChunk],
    *,
    batch_size: int = 32,
) -> list[list[float]]:
    """
    Generate embeddings for a list of TextChunks.

    Returns a list of float vectors in the same order as input chunks.

    Raises:
        RuntimeError: if Ollama is unreachable or returns unexpected dims
    """
    if not chunks:
        return []

    client = ollama.Client(host=settings.ollama_base_url)
    embeddings: list[list[float]] = []
    total = len(chunks)

    logger.info(
        "embedder.start",
        total_chunks=total,
        batch_size=batch_size,
        model=settings.ollama_embed_model,
    )

    for batch_start in range(0, total, batch_size):
        batch = chunks[batch_start : batch_start + batch_size]
        batch_texts = [chunk.content for chunk in batch]

        t0 = time.perf_counter()

        try:
            response = client.embed(
                model=settings.ollama_embed_model,
                input=batch_texts,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Ollama embed call failed at batch {batch_start}: {exc}"
            ) from exc

        elapsed = time.perf_counter() - t0

        batch_embeddings = response.embeddings

        # Sanity check dimensions
        for vec in batch_embeddings:
            if len(vec) != settings.ollama_embed_dimensions:
                raise RuntimeError(
                    f"Expected {settings.ollama_embed_dimensions} dims, "
                    f"got {len(vec)}. Wrong model?"
                )

        embeddings.extend(batch_embeddings)

        logger.info(
            "embedder.batch_complete",
            batch_start=batch_start,
            batch_end=batch_start + len(batch),
            total=total,
            elapsed_seconds=round(elapsed, 2),
        )

    logger.info("embedder.complete", total_embeddings=len(embeddings))
    return embeddings
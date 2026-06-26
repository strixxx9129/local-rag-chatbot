# backend/src/rag/llm_service.py
"""
Ollama LLM service — sync, async, and streaming interfaces.
"""
from typing import AsyncGenerator
import ollama

from src.core.config import settings
from src.core.logging import logger


def generate_answer(
    messages: list[dict],
    *,
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> str:
    """Synchronous Ollama chat — used in RQ workers."""
    client = ollama.Client(host=settings.ollama_base_url)
    logger.info(
        "llm.generate.start",
        model=settings.ollama_chat_model,
        message_count=len(messages),
    )
    try:
        response = client.chat(
            model=settings.ollama_chat_model,
            messages=messages,
            options={"temperature": temperature, "num_predict": max_tokens},
        )
    except Exception as exc:
        logger.error("llm.generate.failed", error=str(exc))
        raise RuntimeError(f"Ollama chat call failed: {exc}") from exc

    answer = response.message.content.strip()
    logger.info("llm.generate.complete", answer_length=len(answer))
    return answer


async def generate_answer_async(
    messages: list[dict],
    *,
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> str:
    """Async buffered Ollama chat — used in FastAPI route handlers."""
    client = ollama.AsyncClient(host=settings.ollama_base_url)
    logger.info(
        "llm.generate_async.start",
        model=settings.ollama_chat_model,
        message_count=len(messages),
    )
    try:
        response = await client.chat(
            model=settings.ollama_chat_model,
            messages=messages,
            options={"temperature": temperature, "num_predict": max_tokens},
        )
    except Exception as exc:
        logger.error("llm.generate_async.failed", error=str(exc))
        raise RuntimeError(f"Ollama async chat call failed: {exc}") from exc

    answer = response.message.content.strip()
    logger.info("llm.generate_async.complete", answer_length=len(answer))
    return answer


async def stream_answer_async(
    messages: list[dict],
    *,
    temperature: float = 0.1,
    max_tokens: int = 1024,
) -> AsyncGenerator[str, None]:
    """
    Async streaming Ollama chat — yields tokens as they arrive.

    Usage:
        async for token in stream_answer_async(messages):
            yield token   # send to SSE client

    Each yielded value is a raw string token fragment — may be a single
    word, a partial word, or punctuation. The caller accumulates them.
    """
    client = ollama.AsyncClient(host=settings.ollama_base_url)

    logger.info(
        "llm.stream.start",
        model=settings.ollama_chat_model,
        message_count=len(messages),
    )

    try:
        # stream=True makes Ollama return an async generator of chunks
        async for chunk in await client.chat(
            model=settings.ollama_chat_model,
            messages=messages,
            stream=True,
            options={"temperature": temperature, "num_predict": max_tokens},
        ):
            token = chunk.message.content
            if token:
                yield token

    except Exception as exc:
        logger.error("llm.stream.failed", error=str(exc))
        raise RuntimeError(f"Ollama stream call failed: {exc}") from exc

    logger.info("llm.stream.complete")


async def embed_query_async(query: str) -> list[float]:
    """Embed a user query string using nomic-embed-text."""
    client = ollama.AsyncClient(host=settings.ollama_base_url)
    try:
        response = await client.embed(
            model=settings.ollama_embed_model,
            input=query,
        )
    except Exception as exc:
        raise RuntimeError(f"Ollama embed call failed: {exc}") from exc

    embeddings = response.embeddings
    if not embeddings:
        raise RuntimeError("Ollama returned empty embeddings for query.")
    return embeddings[0]
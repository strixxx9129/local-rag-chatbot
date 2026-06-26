# backend/src/rag/chunker.py
"""
Text chunking using LangChain's RecursiveCharacterTextSplitter.

Strategy:
  1. Split each page's text independently so we preserve page_number
     attribution per chunk.
  2. Use RecursiveCharacterTextSplitter which tries paragraph → sentence
     → word → character boundaries in order — produces semantically
     coherent chunks.
  3. Estimate token count as len(text) // 4 (rough tiktoken approximation
     without importing tiktoken as a hard dependency).

Chunk size and overlap come from settings so they're tunable without
code changes.
"""
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.config import settings
from src.core.logging import logger
from src.rag.extractor import ExtractedPage


@dataclass
class TextChunk:
    content: str
    chunk_index: int     # global 0-based index across the whole document
    page_number: int     # source page (1-based)
    token_count: int     # approximate


def chunk_pages(pages: list[ExtractedPage]) -> list[TextChunk]:
    """
    Split a list of extracted pages into overlapping text chunks.

    Returns chunks in document order with global chunk_index assigned.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
        is_separator_regex=False,
        strip_whitespace=True,
    )

    all_chunks: list[TextChunk] = []
    global_index = 0

    for page in pages:
        # Split this page's text into sub-chunks
        splits = splitter.split_text(page.text)

        for split_text in splits:
            cleaned = split_text.strip()
            if not cleaned:
                continue

            chunk = TextChunk(
                content=cleaned,
                chunk_index=global_index,
                page_number=page.page_number,
                token_count=len(cleaned) // 4,  # ~4 chars per token
            )
            all_chunks.append(chunk)
            global_index += 1

    logger.info(
        "chunker.complete",
        total_pages=len(pages),
        total_chunks=len(all_chunks),
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    return all_chunks
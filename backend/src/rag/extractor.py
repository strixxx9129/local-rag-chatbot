# backend/src/rag/extractor.py
"""
PDF text extraction using PyMuPDF (fitz).

Extracts text page-by-page, preserving page numbers for citation.
Returns a list of (page_number, text) tuples — 1-based page numbers.

Why page-by-page instead of full document?
  - Lets us attach source page numbers to each chunk
  - Allows skipping blank/image-only pages
  - Keeps memory usage flat on large documents
"""
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from src.core.logging import logger


@dataclass
class ExtractedPage:
    page_number: int   # 1-based
    text: str
    char_count: int


@dataclass
class ExtractionResult:
    pages: list[ExtractedPage]
    page_count: int
    total_chars: int
    file_path: str


def extract_text_from_pdf(file_path: str) -> ExtractionResult:
    """
    Open a PDF and extract text from every page.

    Pages with fewer than 20 characters are treated as blank/image-only
    and excluded — they produce noise in embeddings.

    Raises:
        FileNotFoundError: if file_path doesn't exist
        RuntimeError: if PyMuPDF cannot open the file
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    logger.info("extractor.open", file=file_path)

    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        raise RuntimeError(f"Cannot open PDF '{file_path}': {exc}") from exc

    pages: list[ExtractedPage] = []
    total_chars = 0

    with doc:
        page_count = len(doc)

        for page_num in range(page_count):
            page = doc[page_num]

            # Extract text with layout preservation
            text = page.get_text("text").strip()

            # Skip blank / image-only pages
            if len(text) < 20:
                logger.debug(
                    "extractor.skip_blank_page",
                    page=page_num + 1,
                    chars=len(text),
                )
                continue

            extracted = ExtractedPage(
                page_number=page_num + 1,  # convert to 1-based
                text=text,
                char_count=len(text),
            )
            pages.append(extracted)
            total_chars += len(text)

    logger.info(
        "extractor.complete",
        file=file_path,
        total_pages=page_count,
        extracted_pages=len(pages),
        total_chars=total_chars,
    )

    return ExtractionResult(
        pages=pages,
        page_count=page_count,
        total_chars=total_chars,
        file_path=file_path,
    )
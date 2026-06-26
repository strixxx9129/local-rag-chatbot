# backend/src/workers/document_worker.py
"""
RQ background job: full document processing pipeline.

Pipeline:
  1. Mark document as PROCESSING
  2. Extract text from PDF (PyMuPDF)
  3. Chunk text (RecursiveCharacterTextSplitter)
  4. Generate embeddings (Ollama nomic-embed-text)
  5. Bulk insert chunks + embeddings into PostgreSQL
  6. Mark document as READY

This function runs in a separate worker process — NOT in the FastAPI
process. It uses synchronous SQLAlchemy (database_url_sync) because
RQ workers are synchronous Python processes.

Error handling: any unhandled exception is caught, logged, and the
document is marked FAILED so the user sees a meaningful status.
"""
import uuid

from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import settings
from src.core.logging import logger
from src.models.chunk import DocumentChunk
from src.models.document import Document, DocumentStatus
from src.models.embedding import Embedding
from src.rag.chunker import chunk_pages
from src.rag.embedder import embed_chunks
from src.rag.extractor import extract_text_from_pdf

# Synchronous engine for the worker process
_sync_engine = create_engine(
    settings.database_url_sync,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

SyncSession = sessionmaker(bind=_sync_engine, expire_on_commit=False)


def _mark_status(
    session: Session,
    document_id: uuid.UUID,
    status: DocumentStatus,
    error_message: str | None = None,
) -> None:
    values: dict = {"status": status}
    if error_message:
        values["error_message"] = error_message[:2000]  # truncate long traces
    session.execute(
        update(Document)
        .where(Document.id == document_id)
        .values(**values)
    )
    session.commit()


def process_document(document_id: str, file_path: str) -> None:
    """
    Entry point for the RQ job.

    Args:
        document_id: UUID string of the Document record
        file_path:   Absolute path to the uploaded PDF on disk
    """
    doc_uuid = uuid.UUID(document_id)

    logger.info("worker.start", document_id=document_id)

    with SyncSession() as session:
        # ── Step 1: Mark as PROCESSING ────────────────────────────────────────
        _mark_status(session, doc_uuid, DocumentStatus.PROCESSING)

        try:
            # ── Step 2: Extract text ──────────────────────────────────────────
            logger.info("worker.extract", document_id=document_id)
            extraction = extract_text_from_pdf(file_path)

            if not extraction.pages:
                raise ValueError(
                    "No extractable text found. "
                    "The PDF may be image-only (scanned). "
                    "OCR support is not yet implemented."
                )

            # ── Step 3: Chunk text ────────────────────────────────────────────
            logger.info("worker.chunk", document_id=document_id)
            chunks = chunk_pages(extraction.pages)

            if not chunks:
                raise ValueError("Chunking produced zero chunks.")

            # ── Step 4: Generate embeddings ───────────────────────────────────
            logger.info(
                "worker.embed",
                document_id=document_id,
                total_chunks=len(chunks),
            )
            vectors = embed_chunks(chunks)

            # ── Step 5: Bulk insert chunks + embeddings ───────────────────────
            logger.info("worker.persist", document_id=document_id)

            chunk_objects: list[DocumentChunk] = []

            for chunk, vector in zip(chunks, vectors):
                chunk_obj = DocumentChunk(
                    document_id=doc_uuid,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    token_count=chunk.token_count,
                )
                session.add(chunk_obj)
                chunk_objects.append(chunk_obj)

            # Flush to get IDs
            session.flush()

            for chunk_obj, vector in zip(chunk_objects, vectors):
                emb = Embedding(
                    chunk_id=chunk_obj.id,
                    embedding=vector,
                )
                session.add(emb)

            # ── Step 6: Mark as READY ─────────────────────────────────────────
            session.execute(
                update(Document)
                .where(Document.id == doc_uuid)
                .values(
                    status=DocumentStatus.READY,
                    page_count=extraction.page_count,
                    chunk_count=len(chunks),
                    error_message=None,
                )
            )
            session.commit()

            logger.info(
                "worker.complete",
                document_id=document_id,
                page_count=extraction.page_count,
                chunk_count=len(chunks),
            )

        except Exception as exc:
            logger.exception(
                "worker.failed",
                document_id=document_id,
                error=str(exc),
            )
            _mark_status(
                session,
                doc_uuid,
                DocumentStatus.FAILED,
                error_message=str(exc),
            )
            raise
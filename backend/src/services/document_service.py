# backend/src/services/document_service.py
"""
Document upload orchestration.

Responsibilities:
  1. Validate file type and size
  2. Save file to disk
  3. Create Document DB record (status=PENDING)
  4. Enqueue background processing job
  5. Return immediate response to caller
"""
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.rbac import require_owner_or_superuser
from src.core.config import settings
from src.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from src.core.logging import logger
from src.models.user import User
from src.repositories.document_repository import DocumentRepository
from src.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from src.workers.document_worker import process_document
from src.workers.queue import document_queue

ALLOWED_MIME_TYPES = {"application/pdf"}
MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024


class DocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = DocumentRepository(session)
        self._session = session

    async def upload(
        self,
        file: UploadFile,
        current_user: User,
        *,
        description: str | None = None,
    ) -> DocumentUploadResponse:
        # ── Validate mime type ────────────────────────────────────────────────
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise BadRequestError(
                f"Only PDF files are accepted. Got: {file.content_type}"
            )

        # ── Read file into memory and check size ──────────────────────────────
        content = await file.read()
        if len(content) > MAX_BYTES:
            raise BadRequestError(
                f"File exceeds maximum size of {settings.max_upload_size_mb}MB."
            )

        if len(content) == 0:
            raise BadRequestError("Uploaded file is empty.")

        # ── Determine save path ───────────────────────────────────────────────
        upload_dir = Path(settings.upload_dir) / str(current_user.id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Use UUID-prefixed filename to prevent collisions
        safe_filename = f"{uuid.uuid4()}_{Path(file.filename).name}"
        file_path = upload_dir / safe_filename

        # ── Write to disk ─────────────────────────────────────────────────────
        file_path.write_bytes(content)
        logger.info(
            "document.saved",
            user_id=str(current_user.id),
            path=str(file_path),
            size=len(content),
        )

        # ── Create DB record ──────────────────────────────────────────────────
        title = Path(file.filename).stem.replace("_", " ").replace("-", " ").title()

        doc = await self._repo.create(
            user_id=current_user.id,
            title=title,
            filename=file.filename,
            file_path=str(file_path),
            file_size=len(content),
            mime_type=file.content_type,
            description=description,
        )
        await self._session.commit()

        # ── Enqueue background job ────────────────────────────────────────────
        document_queue.enqueue(
            process_document,
            args=(str(doc.id), str(file_path)),
            job_id=f"doc-{doc.id}",
        )

        logger.info(
            "document.enqueued",
            document_id=str(doc.id),
        )

        return DocumentUploadResponse(
            id=doc.id,
            title=doc.title,
            filename=doc.filename,
            file_size=doc.file_size,
            status=doc.status,
            message="Document uploaded successfully. Processing has started.",
        )

    async def get_document(
        self,
        document_id: uuid.UUID,
        current_user: User,
    ) -> DocumentResponse:
        doc = await self._repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError("Document not found.")
        require_owner_or_superuser(doc.user_id, current_user, "document")
        return DocumentResponse.model_validate(doc)

    async def get_status(
        self,
        document_id: uuid.UUID,
        current_user: User,
    ) -> DocumentStatusResponse:
        doc = await self._repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError("Document not found.")
        require_owner_or_superuser(doc.user_id, current_user, "document")
        return DocumentStatusResponse.model_validate(doc)

    async def list_documents(
        self,
        current_user: User,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> DocumentListResponse:
        docs = await self._repo.get_by_user(
            current_user.id,
            limit=limit,
            offset=offset,
        )
        total = await self._repo.count_by_user(current_user.id)
        return DocumentListResponse(
            documents=[DocumentResponse.model_validate(d) for d in docs],
            total=total,
        )

    async def delete_document(
        self,
        document_id: uuid.UUID,
        current_user: User,
    ) -> None:
        doc = await self._repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError("Document not found.")
        require_owner_or_superuser(doc.user_id, current_user, "document")

        # Remove file from disk
        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()
            logger.info("document.file_deleted", path=str(file_path))

        await self._repo.delete(document_id)
        await self._session.commit()
        logger.info(
            "document.deleted",
            document_id=str(document_id),
            user_id=str(current_user.id),
        )
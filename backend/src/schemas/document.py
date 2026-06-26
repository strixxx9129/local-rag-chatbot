# backend/src/schemas/document.py
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models.document import DocumentStatus


class DocumentUploadResponse(BaseModel):
    """Returned immediately after upload — document is queued for processing."""
    id: uuid.UUID
    title: str
    filename: str
    file_size: int
    status: DocumentStatus
    message: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    filename: str
    file_size: int
    mime_type: str
    page_count: int | None
    chunk_count: int
    status: DocumentStatus
    error_message: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class DocumentStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: DocumentStatus
    chunk_count: int
    page_count: int | None
    error_message: str | None
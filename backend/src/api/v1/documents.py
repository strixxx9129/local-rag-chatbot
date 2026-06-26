# backend/src/api/v1/documents.py
"""
Document management endpoints.

POST   /documents/upload         → upload PDF, enqueue processing
GET    /documents                → list user's documents
GET    /documents/{id}           → get document detail
GET    /documents/{id}/status    → poll processing status
DELETE /documents/{id}           → delete document + file
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.db.session import get_db_session
from src.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from src.schemas.auth import MessageResponse
from src.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


def _get_document_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentService:
    return DocumentService(session)


DocumentServiceDep = Annotated[DocumentService, Depends(_get_document_service)]


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a PDF document for processing",
)
async def upload_document(
    current_user: CurrentUser,
    service: DocumentServiceDep,
    file: UploadFile = File(..., description="PDF file to upload"),
    description: str | None = Form(default=None, max_length=1000),
) -> DocumentUploadResponse:
    return await service.upload(file, current_user, description=description)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all documents for the authenticated user",
)
async def list_documents(
    current_user: CurrentUser,
    service: DocumentServiceDep,
    limit: int = 20,
    offset: int = 0,
) -> DocumentListResponse:
    return await service.list_documents(current_user, limit=limit, offset=offset)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
)
async def get_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    service: DocumentServiceDep,
) -> DocumentResponse:
    return await service.get_document(document_id, current_user)


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Poll document processing status",
)
async def get_document_status(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    service: DocumentServiceDep,
) -> DocumentStatusResponse:
    return await service.get_status(document_id, current_user)


@router.delete(
    "/{document_id}",
    response_model=MessageResponse,
    summary="Delete a document and its file",
)
async def delete_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    service: DocumentServiceDep,
) -> MessageResponse:
    await service.delete_document(document_id, current_user)
    return MessageResponse(message="Document deleted successfully.")
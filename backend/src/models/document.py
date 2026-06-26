# backend/src/models/document.py
import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.user import User
    from src.models.chunk import DocumentChunk


class DocumentStatus(str, enum.Enum):
    """
    Lifecycle of a document through the processing pipeline.

    PENDING   → uploaded, waiting for worker
    PROCESSING → worker is extracting / chunking / embedding
    READY     → all embeddings stored, document is searchable
    FAILED    → pipeline error, inspect error_message
    """
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="application/pdf",
    )
    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"),
        nullable=False,
        default=DocumentStatus.PENDING,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="documents",
        lazy="select",
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} title={self.title} status={self.status}>"
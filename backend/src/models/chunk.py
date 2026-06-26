# backend/src/models/chunk.py
import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Computed

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.document import Document
    from src.models.embedding import Embedding
    from src.models.message import MessageCitation


class DocumentChunk(UUIDMixin, TimestampMixin, Base):
    """
    One logical chunk of a document's extracted text.

    chunk_index  : 0-based position within the document
    page_number  : source page (1-based), populated when extractable
    token_count  : approximate token count used for RAG context budgeting
    content_tsv  : generated tsvector column for PostgreSQL full-text search
    """

    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    # Generated column — PostgreSQL computes this, SQLAlchemy reads it
    content_tsv: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', content)", persisted=True),
        nullable=True,
        server_default=None,
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
        lazy="select",
    )
    embedding: Mapped["Embedding | None"] = relationship(
        "Embedding",
        back_populates="chunk",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="select",
    )
    citations: Mapped[list["MessageCitation"]] = relationship(
        "MessageCitation",
        back_populates="chunk",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk id={self.id} "
            f"doc={self.document_id} idx={self.chunk_index}>"
        )
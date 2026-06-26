# backend/src/models/message.py
import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.conversation import Conversation
    from src.models.chunk import DocumentChunk


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(UUIDMixin, TimestampMixin, Base):
    """
    A single turn in a Conversation.

    role        : who authored this message
    content     : raw text of the message
    token_count : used for context-window budgeting in Phase 8 memory
    citations   : which chunks the assistant cited (populated for ASSISTANT role)
    """

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
        lazy="select",
    )
    citations: Mapped[list["MessageCitation"]] = relationship(
        "MessageCitation",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<Message id={self.id} role={self.role} "
            f"conv={self.conversation_id}>"
        )


class MessageCitation(UUIDMixin, Base):
    """
    Junction table: which DocumentChunks were cited in a Message.

    relevance_score : cosine similarity score returned by retriever
    citation_index  : display order of citations in the response (0-based)
    """

    __tablename__ = "message_citations"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relevance_score: Mapped[float | None] = mapped_column(
        nullable=True,
    )
    citation_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Relationships
    message: Mapped["Message"] = relationship(
        "Message",
        back_populates="citations",
        lazy="select",
    )
    chunk: Mapped["DocumentChunk"] = relationship(
        "DocumentChunk",
        back_populates="citations",
        lazy="select",
    )
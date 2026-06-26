# backend/src/models/memory.py
"""
ConversationMemory stores compressed semantic summaries of conversation
turns as vector embeddings for long-term memory retrieval.

Each record represents a summarized window of N messages from a
conversation. When a user asks a question, we embed the query and
search these records to surface relevant past context.

Why a separate table from Embedding?
  Embedding.chunk_id → DocumentChunk (document content)
  ConversationMemory.conversation_id → Conversation (user history)
  These are fundamentally different data types with different
  retrieval patterns and lifecycle rules.
"""
import uuid
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.config import settings
from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.conversation import Conversation


class ConversationMemory(UUIDMixin, TimestampMixin, Base):
    """
    A semantic memory unit — a summarized window of conversation turns.

    Fields:
        conversation_id : which conversation this memory belongs to
        summary         : human-readable compressed summary of the window
        embedding       : vector of the summary (for semantic retrieval)
        message_window  : which message indices this summary covers (e.g. "0-9")
        turn_start      : first message index in the window (0-based)
        turn_end        : last message index in the window (0-based)
        model_name      : which embed model produced this vector
    """

    __tablename__ = "conversation_memories"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.ollama_embed_dimensions),
        nullable=False,
    )
    message_window: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="",
    )
    turn_start: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    turn_end: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    model_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default=settings.ollama_embed_model,
    )

    # Relationship
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        lazy="select",
    )

    __table_args__ = (
        Index(
            "ix_conversation_memories_hnsw_cosine",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ConversationMemory id={self.id} "
            f"conv={self.conversation_id} window={self.message_window}>"
        )
# backend/src/models/conversation.py
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.user import User
    from src.models.document import Document
    from src.models.message import Message


class Conversation(UUIDMixin, TimestampMixin, Base):
    """
    A named chat session belonging to one user.

    document_id is nullable — users can have a general conversation
    not tied to a specific document, or one scoped to a single document.
    """

    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="New Conversation",
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="conversations",
        lazy="select",
    )
    document: Mapped["Document | None"] = relationship(
        "Document",
        lazy="select",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} title={self.title}>"
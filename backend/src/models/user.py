# backend/src/models/user.py
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.document import Document
    from src.models.conversation import Conversation


class User(UUIDMixin, TimestampMixin, Base):
    """
    Application user.

    Passwords are stored as bcrypt hashes — never plaintext.
    is_active lets us soft-disable accounts without deletion.
    is_superuser gates admin-only endpoints.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    refresh_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="select",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
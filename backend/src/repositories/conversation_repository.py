# backend/src/repositories/conversation_repository.py
"""
DB operations for Conversation and Message models.
"""
import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.conversation import Conversation
from src.models.message import Message, MessageCitation, MessageRole


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Conversation ──────────────────────────────────────────────────────────

    async def create_conversation(
        self,
        *,
        user_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
        title: str = "New Conversation",
    ) -> Conversation:
        convo = Conversation(
            user_id=user_id,
            document_id=document_id,
            title=title,
        )
        self._session.add(convo)
        await self._session.flush()
        await self._session.refresh(convo)
        return convo

    async def get_conversation(
        self,
        conversation_id: uuid.UUID,
    ) -> Conversation | None:
        result = await self._session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    async def get_user_conversations(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[Conversation]:
        result = await self._session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    # ── Message ───────────────────────────────────────────────────────────────

    async def add_message(
        self,
        *,
        conversation_id: uuid.UUID,
        role: MessageRole,
        content: str,
        token_count: int | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            token_count=token_count,
        )
        self._session.add(msg)
        await self._session.flush()
        await self._session.refresh(msg)
        return msg

    async def add_citations(
        self,
        message_id: uuid.UUID,
        chunks: list[dict],
    ) -> None:
        """
        chunks: list of dicts with keys: chunk_id, relevance_score, citation_index
        """
        for item in chunks:
            citation = MessageCitation(
                message_id=message_id,
                chunk_id=item["chunk_id"],
                relevance_score=item.get("relevance_score"),
                citation_index=item.get("citation_index", 0),
            )
            self._session.add(citation)
        await self._session.flush()

    async def get_recent_messages(
        self,
        conversation_id: uuid.UUID,
        *,
        limit: int = 10,
    ) -> Sequence[Message]:
        """Return the N most recent messages for conversation history."""
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        # Return in chronological order
        return list(reversed(messages))
# backend/src/repositories/memory_repository.py
"""
DB operations for ConversationMemory.

Two key operations:
  1. store()   — persist a new memory summary + embedding
  2. retrieve() — vector similarity search over a user's memories
"""
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logging import logger
from src.models.memory import ConversationMemory


class MemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def store(
        self,
        *,
        conversation_id: uuid.UUID,
        summary: str,
        embedding: list[float],
        turn_start: int,
        turn_end: int,
    ) -> ConversationMemory:
        """Persist a new conversation memory record."""
        memory = ConversationMemory(
            conversation_id=conversation_id,
            summary=summary,
            embedding=embedding,
            message_window=f"{turn_start}-{turn_end}",
            turn_start=turn_start,
            turn_end=turn_end,
            model_name=settings.ollama_embed_model,
        )
        self._session.add(memory)
        await self._session.flush()
        await self._session.refresh(memory)

        logger.info(
            "memory_repo.stored",
            conversation_id=str(conversation_id),
            window=f"{turn_start}-{turn_end}",
        )
        return memory

    async def retrieve_similar(
        self,
        *,
        query_embedding: list[float],
        user_conversation_ids: list[uuid.UUID],
        top_k: int = 3,
        similarity_threshold: float = 0.5,
    ) -> list[dict]:
        """
        Find the most semantically similar memory records across
        a user's conversations.

        Args:
            query_embedding:        Embedded user query vector
            user_conversation_ids:  UUIDs of conversations to search within
            top_k:                  Max memories to return
            similarity_threshold:   Min similarity score (0.0 - 1.0)

        Returns:
            List of dicts with keys: summary, similarity_score,
            conversation_id, message_window
        """
        if not user_conversation_ids:
            return []

        embedding_str = (
            "[" + ",".join(str(v) for v in query_embedding) + "]"
        )

        stmt = (
            select(
                ConversationMemory.id,
                ConversationMemory.conversation_id,
                ConversationMemory.summary,
                ConversationMemory.message_window,
                ConversationMemory.turn_start,
                ConversationMemory.turn_end,
                (
                    1 - ConversationMemory.embedding.cosine_distance(
                        text(f"'{embedding_str}'::vector")
                    )
                ).label("similarity_score"),
            )
            .where(
                ConversationMemory.conversation_id.in_(user_conversation_ids)
            )
            .order_by(
                ConversationMemory.embedding.cosine_distance(
                    text(f"'{embedding_str}'::vector")
                )
            )
            .limit(top_k * 2)   # over-fetch, filter by threshold below
        )

        result = await self._session.execute(stmt)
        rows = result.mappings().all()

        memories = []
        for row in rows:
            score = float(row["similarity_score"])
            if score < similarity_threshold:
                continue
            memories.append({
                "summary": row["summary"],
                "similarity_score": round(score, 4),
                "conversation_id": str(row["conversation_id"]),
                "message_window": row["message_window"],
            })

        return memories[:top_k]

    async def get_conversation_memory_count(
        self,
        conversation_id: uuid.UUID,
    ) -> int:
        """Return how many memory records exist for a conversation."""
        from sqlalchemy import func
        result = await self._session.execute(
            select(func.count(ConversationMemory.id)).where(
                ConversationMemory.conversation_id == conversation_id
            )
        )
        return result.scalar_one()

    async def get_latest_turn_end(
        self,
        conversation_id: uuid.UUID,
    ) -> int:
        """
        Return the highest turn_end stored for this conversation.
        Used to determine where to start the next memory window.
        """
        result = await self._session.execute(
            select(ConversationMemory.turn_end)
            .where(ConversationMemory.conversation_id == conversation_id)
            .order_by(ConversationMemory.turn_end.desc())
            .limit(1)
        )
        val = result.scalar_one_or_none()
        return val if val is not None else -1
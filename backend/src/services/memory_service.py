# backend/src/services/memory_service.py
"""
Memory service — orchestrates summarization, storage, and retrieval
of long-term conversation memory.

Two public interfaces:
  maybe_summarize()   → called after each assistant turn; triggers
                         summarization when the message threshold is hit
  retrieve_memories() → called at the start of each RAG turn to surface
                         relevant past context

Summarization prompt:
  We ask llama3:8b to compress N conversation turns into a concise
  factual summary. The summary is then embedded with nomic-embed-text
  and stored as a ConversationMemory record.
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logging import logger
from src.models.message import MessageRole
from src.rag.llm_service import embed_query_async, generate_answer_async
from src.repositories.conversation_repository import ConversationRepository
from src.repositories.memory_repository import MemoryRepository

# Summarize every N messages (user + assistant combined)
SUMMARIZATION_THRESHOLD = 10

SUMMARIZATION_PROMPT_TEMPLATE = """You are a conversation summarizer.
Summarize the following conversation turns into a concise factual summary.
Focus on: key topics discussed, questions asked, answers given, and
important facts mentioned. Be brief — 3 to 5 sentences maximum.

Conversation turns:
{turns}

Concise summary:"""


class MemoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._memory_repo = MemoryRepository(session)
        self._convo_repo = ConversationRepository(session)

    # ── Summarization ─────────────────────────────────────────────────────────

    async def maybe_summarize(
        self,
        conversation_id: uuid.UUID,
    ) -> bool:
        """
        Check if summarization is needed and run it if so.

        Summarization triggers when:
          total_messages - last_summarized_turn_end > SUMMARIZATION_THRESHOLD

        Returns True if summarization was performed.
        """
        # Get all messages for this conversation
        messages = await self._convo_repo.get_recent_messages(
            conversation_id,
            limit=200,   # enough to cover any practical conversation
        )

        if len(messages) < SUMMARIZATION_THRESHOLD:
            return False

        # Find where the last memory window ended
        last_turn_end = await self._memory_repo.get_latest_turn_end(
            conversation_id
        )
        unsummarized_start = last_turn_end + 1

        # Count unsummarized messages
        unsummarized = messages[unsummarized_start:]
        if len(unsummarized) < SUMMARIZATION_THRESHOLD:
            return False

        # Take exactly SUMMARIZATION_THRESHOLD messages to summarize
        window = unsummarized[:SUMMARIZATION_THRESHOLD]
        turn_start = unsummarized_start
        turn_end = unsummarized_start + len(window) - 1

        logger.info(
            "memory_service.summarize_start",
            conversation_id=str(conversation_id),
            turn_start=turn_start,
            turn_end=turn_end,
        )

        # Build turns text
        turns_text = "\n".join(
            f"{msg.role.value.upper()}: {msg.content}"
            for msg in window
        )

        # Generate summary via Ollama
        summary = await self._summarize_turns(turns_text)

        # Embed the summary
        embedding = await embed_query_async(summary)

        # Persist
        await self._memory_repo.store(
            conversation_id=conversation_id,
            summary=summary,
            embedding=embedding,
            turn_start=turn_start,
            turn_end=turn_end,
        )
        await self._session.commit()

        logger.info(
            "memory_service.summarize_complete",
            conversation_id=str(conversation_id),
            summary_length=len(summary),
        )

        return True

    async def _summarize_turns(self, turns_text: str) -> str:
        """Call Ollama to summarize conversation turns."""
        prompt = SUMMARIZATION_PROMPT_TEMPLATE.format(turns=turns_text)
        messages = [{"role": "user", "content": prompt}]
        try:
            summary = await generate_answer_async(
                messages,
                temperature=0.0,    # deterministic summaries
                max_tokens=300,
            )
            return summary.strip()
        except Exception as exc:
            logger.warning(
                "memory_service.summarize_failed",
                error=str(exc),
            )
            # Fallback: truncate turns as the summary
            return turns_text[:500]

    # ── Retrieval ─────────────────────────────────────────────────────────────

    async def retrieve_memories(
        self,
        *,
        query: str,
        query_embedding: list[float],
        user_id: uuid.UUID,
        current_conversation_id: uuid.UUID | None = None,
        top_k: int = 3,
    ) -> list[dict]:
        """
        Retrieve semantically relevant past conversation memories.

        Searches across ALL of the user's conversations (not just the
        current one) to surface relevant context from prior sessions.

        Args:
            query:                   User's current question
            query_embedding:         Pre-computed query vector
            user_id:                 Search within this user's conversations
            current_conversation_id: Exclude the current conversation
                                     (it's already in session memory)
            top_k:                   Max memories to return

        Returns:
            List of memory dicts with: summary, similarity_score,
            conversation_id, message_window
        """
        # Get all conversation IDs for this user (excluding current)
        conversations = await self._convo_repo.get_user_conversations(
            user_id,
            limit=100,
        )

        convo_ids = [
            c.id for c in conversations
            if current_conversation_id is None
            or c.id != current_conversation_id
        ]

        if not convo_ids:
            return []

        memories = await self._memory_repo.retrieve_similar(
            query_embedding=query_embedding,
            user_conversation_ids=convo_ids,
            top_k=top_k,
        )

        logger.info(
            "memory_service.retrieve_complete",
            user_id=str(user_id),
            searched_conversations=len(convo_ids),
            memories_found=len(memories),
        )

        return memories

    async def get_session_context(
        self,
        conversation_id: uuid.UUID,
        *,
        limit: int = 6,
    ) -> list[dict]:
        """
        Return recent session turns as message dicts.
        Used directly in prompt construction.
        """
        messages = await self._convo_repo.get_recent_messages(
            conversation_id,
            limit=limit,
        )
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
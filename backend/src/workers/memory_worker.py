# backend/src/workers/memory_worker.py
"""
RQ background job: trigger memory summarization after each assistant turn.

This runs asynchronously so the user never waits for summarization.
The job is enqueued by the generator node after persisting the assistant
message. It uses the sync DB session (same pattern as document_worker).
"""
import asyncio
import uuid

from src.core.logging import logger


def summarize_conversation(conversation_id: str) -> None:
    """
    RQ job entry point — summarize a conversation if threshold is met.

    Runs the async MemoryService in a fresh event loop.
    This is safe because RQ workers are synchronous processes.
    """
    logger.info(
        "memory_worker.start",
        conversation_id=conversation_id,
    )

    async def _run() -> None:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        from src.db.session import engine
        from src.services.memory_service import MemoryService

        AsyncSessionLocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with AsyncSessionLocal() as session:
            service = MemoryService(session)
            summarized = await service.maybe_summarize(
                uuid.UUID(conversation_id)
            )
            if summarized:
                logger.info(
                    "memory_worker.complete",
                    conversation_id=conversation_id,
                    summarized=True,
                )
            else:
                logger.info(
                    "memory_worker.skipped",
                    conversation_id=conversation_id,
                    reason="threshold not reached",
                )

    asyncio.run(_run())
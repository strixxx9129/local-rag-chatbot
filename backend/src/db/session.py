# backend/src/db/session.py
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import settings
from src.core.logging import logger

engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,       # drops stale connections before use
    pool_recycle=3600,        # recycle connections every hour
    echo=settings.app_debug,  # log SQL only in debug mode
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # keep attribute access after commit
    autoflush=False,
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields one AsyncSession per request
    and guarantees rollback on error.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("db.session.rollback")
            raise
        finally:
            await session.close()
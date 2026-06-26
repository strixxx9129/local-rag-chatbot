# backend/tests/test_db.py
"""
Smoke tests for the database layer.
These tests run against a real PostgreSQL instance (not mocked).
"""
import asyncio
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import AsyncSessionFactory
from src.models import User, Document, DocumentChunk, Embedding, Conversation, Message
from src.models.document import DocumentStatus
from src.models.message import MessageRole


# @pytest.fixture(scope="session")
# def event_loop():
#     loop = asyncio.new_event_loop()
#     yield loop
#     loop.close()


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        yield session
        await session.rollback()


# @pytest.mark.asyncio
# async def test_pgvector_extension(db: AsyncSession) -> None:
#     result = await db.execute(
#         text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
#     )
#     assert result.scalar_one() == "vector"
@pytest.mark.asyncio
async def test_database_connection(db: AsyncSession) -> None:
    result = await db.execute(text("SELECT 1"))
    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_create_user(db: AsyncSession) -> None:
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="$2b$12$fakehash",
        full_name="Test User",
    )
    db.add(user)
    await db.flush()  # assigns id without committing

    assert user.id is not None
    assert user.is_active is True
    assert user.is_superuser is False


@pytest.mark.asyncio
async def test_document_status_default(db: AsyncSession) -> None:
    user = User(
        email="doc@example.com",
        username="docuser",
        hashed_password="$2b$12$fakehash",
    )
    db.add(user)
    await db.flush()

    doc = Document(
        user_id=user.id,
        title="Test PDF",
        filename="test.pdf",
        file_path="/uploads/test.pdf",
        file_size=12345,
    )
    db.add(doc)
    await db.flush()

    assert doc.status == DocumentStatus.PENDING
    assert doc.chunk_count == 0


@pytest.mark.asyncio
async def test_embedding_vector_insert(db: AsyncSession) -> None:
    user = User(
        email="emb@example.com",
        username="embuser",
        hashed_password="$2b$12$fakehash",
    )
    db.add(user)
    await db.flush()

    doc = Document(
        user_id=user.id,
        title="Embed Test",
        filename="embed.pdf",
        file_path="/uploads/embed.pdf",
        file_size=999,
    )
    db.add(doc)
    await db.flush()

    chunk = DocumentChunk(
        document_id=doc.id,
        content="The quick brown fox",
        chunk_index=0,
        page_number=1,
    )
    db.add(chunk)
    await db.flush()

    # Insert a fake 768-dim vector (all 0.1)
    fake_vector = [0.1] * 768
    embedding = Embedding(
        chunk_id=chunk.id,
        embedding=fake_vector,
    )
    db.add(embedding)
    await db.flush()

    assert embedding.id is not None
    assert len(embedding.embedding) == 768
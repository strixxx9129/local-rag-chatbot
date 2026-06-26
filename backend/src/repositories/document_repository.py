# backend/src/repositories/document_repository.py
import uuid
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.chunk import DocumentChunk
from src.models.document import Document, DocumentStatus
from src.models.embedding import Embedding


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Document CRUD ─────────────────────────────────────────────────────────

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        title: str,
        filename: str,
        file_path: str,
        file_size: int,
        mime_type: str = "application/pdf",
        description: str | None = None,
    ) -> Document:
        doc = Document(
            user_id=user_id,
            title=title,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            description=description,
        )
        self._session.add(doc)
        await self._session.flush()
        await self._session.refresh(doc)
        return doc

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Document]:
        result = await self._session.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        from sqlalchemy import func
        result = await self._session.execute(
            select(func.count(Document.id)).where(Document.user_id == user_id)
        )
        return result.scalar_one()

    async def set_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
        *,
        error_message: str | None = None,
    ) -> None:
        values: dict = {"status": status}
        if error_message is not None:
            values["error_message"] = error_message
        await self._session.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(**values)
        )
        await self._session.commit()

    async def set_processing_complete(
        self,
        document_id: uuid.UUID,
        *,
        page_count: int,
        chunk_count: int,
    ) -> None:
        await self._session.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(
                status=DocumentStatus.READY,
                page_count=page_count,
                chunk_count=chunk_count,
                error_message=None,
            )
        )
        await self._session.commit()

    async def delete(self, document_id: uuid.UUID) -> None:
        doc = await self.get_by_id(document_id)
        if doc:
            await self._session.delete(doc)

    # ── Chunk + Embedding insert (bulk) ───────────────────────────────────────

    async def bulk_insert_chunks_and_embeddings(
        self,
        document_id: uuid.UUID,
        chunks: list[dict],
    ) -> int:
        """
        Insert all chunks and their embeddings in one transaction.

        chunks: list of dicts with keys:
            content, chunk_index, page_number, token_count, embedding_vector
        """
        chunk_objects: list[DocumentChunk] = []

        for item in chunks:
            chunk = DocumentChunk(
                document_id=document_id,
                content=item["content"],
                chunk_index=item["chunk_index"],
                page_number=item.get("page_number"),
                token_count=item.get("token_count"),
            )
            self._session.add(chunk)
            chunk_objects.append(chunk)

        # Flush to get chunk IDs assigned
        await self._session.flush()

        # Now insert embeddings referencing the chunk IDs
        for chunk_obj, item in zip(chunk_objects, chunks):
            embedding = Embedding(
                chunk_id=chunk_obj.id,
                embedding=item["embedding_vector"],
            )
            self._session.add(embedding)

        await self._session.flush()
        return len(chunk_objects)
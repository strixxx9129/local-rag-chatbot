# backend/src/models/embedding.py
import uuid
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector

# from sqlalchemy.dialects.postgresql import JSONB


from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.config import settings
from src.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.chunk import DocumentChunk


class Embedding(UUIDMixin, TimestampMixin, Base):
    """
    Vector embedding for a single DocumentChunk.

    model_name   : which Ollama model produced this vector
                   (lets us invalidate embeddings if we switch models)
    dimensions   : sanity-check column — must match pgvector index dims
    embedding    : the actual float32 vector stored by pgvector

    Index strategy:
        HNSW    → high recall, fast ANN search, recommended for production
        ivfflat → alternative, lower memory, slightly lower recall

    We use HNSW with cosine distance because nomic-embed-text
    vectors are L2-normalized, making cosine ≡ dot product.
    """

    __tablename__ = "embeddings"

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,          # enforces 1:1 with chunk
        index=True,
    )
    model_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default=settings.ollama_embed_model,
    )
    dimensions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=settings.ollama_embed_dimensions,
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.ollama_embed_dimensions),
        nullable=False,
    )
    # embedding: Mapped[list[float]] = mapped_column(
    #     JSONB,
    #     nullable=False,
    # )

    # Relationships
    chunk: Mapped["DocumentChunk"] = relationship(
        "DocumentChunk",
        back_populates="embedding",
        lazy="select",
    )

    __table_args__ = (
        # HNSW index for approximate nearest-neighbor search
        # m=16, ef_construction=64 are solid production defaults
        Index(
            "ix_embeddings_hnsw_cosine",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
    

    def __repr__(self) -> str:
        return (
            f"<Embedding id={self.id} "
            f"chunk={self.chunk_id} model={self.model_name}>"
        )
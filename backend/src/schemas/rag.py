# backend/src/schemas/rag.py
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models.document import DocumentStatus


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""
    question: str = Field(min_length=1, max_length=2000)
    document_id: uuid.UUID | None = Field(default=None)
    conversation_id: uuid.UUID | None = Field(default=None)
    top_k: int = Field(default=5, ge=1, le=20)
    use_hybrid: bool = Field(
        default=True,
        description="Use hybrid search (vector + FTS). "
                    "Set False to use pure vector search only.",
    )
    vector_weight: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="RRF weight for vector results (only used when use_hybrid=True).",
    )
    fts_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="RRF weight for FTS results (only used when use_hybrid=True).",
    )


class CitationResponse(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    page_number: int | None
    content_snippet: str
    relevance_score: float


class ChatResponse(BaseModel):
    answer: str
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    citations: list[CitationResponse]
    model: str
    retrieved_chunks: int
    search_mode: str    # "hybrid" | "vector"


class RetrievedChunk(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    content: str
    page_number: int | None
    chunk_index: int
    similarity_score: float
# backend/src/models/__init__.py
# Re-export every model so Alembic's autogenerate can discover them
# by importing this single module.

from src.models.user import User
from src.models.document import Document, DocumentStatus
from src.models.chunk import DocumentChunk
from src.models.embedding import Embedding
from src.models.conversation import Conversation
from src.models.message import Message, MessageCitation, MessageRole
from src.models.memory import ConversationMemory 

__all__ = [
    "User",
    "Document",
    "DocumentStatus",
    "DocumentChunk",
    "Embedding",
    "Conversation",
    "Message",
    "MessageCitation",
    "MessageRole",
    "ConversationMemory",
]
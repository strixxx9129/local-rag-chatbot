# backend/src/api/v1/rag.py
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.db.session import get_db_session
from src.repositories.conversation_repository import ConversationRepository
from src.schemas.rag import ChatRequest, ChatResponse
from src.services.graph_service import GraphService   # ← NOW uses GraphService

router = APIRouter(prefix="/rag", tags=["RAG"])


def _get_graph_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GraphService:
    return GraphService(session)


GraphServiceDep = Annotated[GraphService, Depends(_get_graph_service)]


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask a question — LangGraph agent returns answer + citations",
)
async def chat(
    request: ChatRequest,
    current_user: CurrentUser,
    service: GraphServiceDep,
) -> ChatResponse:
    return await service.chat(request, current_user)


@router.get("/conversations", summary="List conversations")
async def list_conversations(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = 20,
    offset: int = 0,
) -> dict:
    repo = ConversationRepository(session)
    convos = await repo.get_user_conversations(
        current_user.id, limit=limit, offset=offset
    )
    return {
        "conversations": [
            {
                "id": str(c.id),
                "title": c.title,
                "document_id": str(c.document_id) if c.document_id else None,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in convos
        ],
        "total": len(convos),
    }


@router.get("/conversations/{conversation_id}", summary="Get conversation messages")
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    repo = ConversationRepository(session)
    convo = await repo.get_conversation(conversation_id)

    if not convo or convo.user_id != current_user.id:
        from src.core.exceptions import NotFoundError
        raise NotFoundError("Conversation not found.")

    return {
        "id": str(convo.id),
        "title": convo.title,
        "document_id": str(convo.document_id) if convo.document_id else None,
        "messages": [
            {
                "id": str(m.id),
                "role": m.role.value,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in convo.messages
        ],
        "created_at": convo.created_at.isoformat(),
    }
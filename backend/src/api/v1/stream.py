# backend/src/api/v1/stream.py
"""
SSE streaming endpoint.

GET  /stream/chat   → streams RAG answer as Server-Sent Events

Why GET with query params instead of POST with body?
  EventSource (browser native SSE) only supports GET requests.
  We use fetch + ReadableStream on the frontend instead, which
  supports POST — so POST is correct here. EventSource is not used.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.db.session import get_db_session
from src.schemas.rag import ChatRequest
from src.services.stream_service import StreamService

router = APIRouter(prefix="/stream", tags=["Streaming"])


def _get_stream_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StreamService:
    return StreamService(session)


StreamServiceDep = Annotated[StreamService, Depends(_get_stream_service)]


@router.post(
    "/chat",
    summary="Stream a RAG answer as Server-Sent Events",
    response_class=StreamingResponse,
)
async def stream_chat(
    request: ChatRequest,
    current_user: CurrentUser,
    service: StreamServiceDep,
) -> StreamingResponse:
    """
    Stream the RAG pipeline response token-by-token.

    Response format: text/event-stream
    Each event: data: {"type": "...", "content": "..."}

    Event types:
      status   → pipeline progress message ("Searching documents...")
      token    → single LLM token fragment
      metadata → citations + conversation_id + message_id (sent once, after tokens)
      done     → stream complete signal
      error    → pipeline error (stream ends after this)
    """
    return StreamingResponse(
        service.stream_chat(request, current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",      # disable Nginx buffering
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
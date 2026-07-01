from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import StreamingResponse

from app.api.deps import ChatRepoDep, CurrentUserDep
from app.core.exceptions import NotFoundError
from app.models.chat import ChatSession
from app.schemas.chat import (
    ChatMessageCreate,
    ChatSessionCreate,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
)
from app.services.rag.chat import ChatService

router = APIRouter()


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
)
async def create_chat_session(
    payload: ChatSessionCreate,
    chat_repo: ChatRepoDep,
    current_user: CurrentUserDep,
) -> ChatSession:
    """Create a new RAG conversation workspace for the user."""
    session_data = {
        "user_id": current_user.id,
        "title": payload.title,
        "is_pinned": False,
    }
    session = await chat_repo.create(session_data)
    await chat_repo.session.commit()
    return session


@router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
    summary="List all chat sessions",
)
async def list_chat_sessions(
    chat_repo: ChatRepoDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 50,
) -> dict:
    """Retrieve all conversations created by the user, ordered descending by date."""
    items, total = await chat_repo.get_multi_by_user(current_user.id, skip=skip, limit=limit)
    page = (skip // limit) + 1 if limit else 1
    return {"items": items, "total": total, "page": page, "page_size": limit, "total_pages": max(1, -(-total // limit)) if limit else 1}


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionDetailResponse,
    summary="Get chat session details",
)
async def get_chat_session(
    session_id: uuid.UUID,
    chat_repo: ChatRepoDep,
    current_user: CurrentUserDep,
) -> ChatSession:
    """Retrieve detail schema of a chat session including its messages."""
    session = await chat_repo.get_by_id_and_user(session_id, current_user.id)
    if not session:
        raise NotFoundError("Chat session not found.")
    return session


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat session",
)
async def delete_chat_session(
    session_id: uuid.UUID,
    chat_repo: ChatRepoDep,
    current_user: CurrentUserDep,
) -> Response:
    """Permanently delete a chat session and its nested transcripts."""
    session = await chat_repo.get_by_id_and_user(session_id, current_user.id)
    if not session:
        raise NotFoundError("Chat session not found.")

    await chat_repo.delete_by_user(session_id, current_user.id)
    await chat_repo.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a chat session (rename/pin)",
)
async def update_chat_session(
    session_id: uuid.UUID,
    body: dict,
    chat_repo: ChatRepoDep,
    current_user: CurrentUserDep,
) -> ChatSession:
    """Rename a chat session title or toggle its pinned state."""
    session = await chat_repo.get_by_id_and_user(session_id, current_user.id)
    if not session:
        raise NotFoundError("Chat session not found.")

    if "title" in body and isinstance(body["title"], str):
        session.title = body["title"].strip() or "Untitled Chat"
    if "is_pinned" in body and isinstance(body["is_pinned"], bool):
        session.is_pinned = body["is_pinned"]

    chat_repo.session.add(session)
    await chat_repo.session.commit()
    return session


@router.post(
    "/sessions/{session_id}/messages",
    summary="Send a message to a session and stream RAG response",
)
async def send_message(
    session_id: uuid.UUID,
    payload: ChatMessageCreate,
    chat_repo: ChatRepoDep,
    current_user: CurrentUserDep,
) -> StreamingResponse:
    """Submit a message and stream back Server-Sent Events containing text tokens and source citations."""
    session = await chat_repo.get_by_id_and_user(session_id, current_user.id)
    if not session:
        raise NotFoundError("Chat session not found.")

    chat_service = ChatService()
    generator = chat_service.stream_chat_response(
        session_id,
        current_user.id,
        payload.content,
        document_ids=payload.document_ids,
        multi_query=payload.multi_query,
        expand_context=payload.expand_context,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disables buffering in reverse proxies like Nginx
        },
    )

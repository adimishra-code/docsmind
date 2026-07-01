from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.chat import ChatMessage, ChatSession
from app.repositories.base import BaseRepository


class ChatRepository(BaseRepository[ChatSession]):
    def __init__(self, session: Any) -> None:
        super().__init__(ChatSession, session)

    async def get_by_id_and_user(self, session_id: uuid.UUID, user_id: uuid.UUID) -> ChatSession | None:
        """Retrieve a specific chat session with its messages preloaded, scoped by user_id."""
        query = (
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.messages))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_multi_by_user(
        self, user_id: uuid.UUID, *, skip: int = 0, limit: int = 50
    ) -> tuple[list[ChatSession], int]:
        """Fetch all paginated chat sessions belonging to a specific user."""
        # Get count
        from sqlalchemy import func
        count_stmt = select(func.count()).select_from(ChatSession).where(ChatSession.user_id == user_id)
        count_res = await self.session.execute(count_stmt)
        total = count_res.scalar_one()

        # Get items
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items_res = await self.session.execute(stmt)
        items = list(items_res.scalars().all())

        return items, total

    async def delete_by_user(self, session_id: uuid.UUID, user_id: uuid.UUID) -> ChatSession | None:
        """Delete a chat session, automatically cascading to its child messages."""
        db_obj = await self.get_by_id_and_user(session_id, user_id)
        if db_obj:
            await self.session.delete(db_obj)
            await self.session.flush()
        return db_obj


class MessageRepository(BaseRepository[ChatMessage]):
    def __init__(self, session: Any) -> None:
        super().__init__(ChatMessage, session)

    async def get_by_session(self, session_id: uuid.UUID) -> list[ChatMessage]:
        """Fetch all chat messages belonging to a specific chat session."""
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

from __future__ import annotations

import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Document, session)

    async def get_by_id_and_user(self, doc_id: uuid.UUID, user_id: uuid.UUID) -> Document | None:
        """Retrieve a specific document ensuring the user owns it."""
        query = select(Document).where(Document.id == doc_id, Document.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_multi_by_user(
        self, user_id: uuid.UUID, *, skip: int = 0, limit: int = 100
    ) -> tuple[list[Document], int]:
        """Fetch paginated documents owned by the user, returning items and total count."""
        # Query total count
        count_query = select(func.count()).select_from(Document).where(Document.user_id == user_id)
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Query items
        query = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def delete_by_user(self, doc_id: uuid.UUID, user_id: uuid.UUID) -> Document | None:
        """Delete document record ensuring owner authorization matches user_id."""
        db_obj = await self.get_by_id_and_user(doc_id, user_id)
        if db_obj:
            await self.session.delete(db_obj)
            await self.session.flush()
        return db_obj

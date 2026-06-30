from __future__ import annotations

from typing import Any, Generic, Type, TypeVar
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository providing basic CRUD operations.

    Subclasses should override or extend these methods for custom query logic.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get(self, id: uuid.UUID) -> ModelType | None:
        """Fetch a single record by primary key UUID."""
        return await self.session.get(self.model, id)

    async def get_multi(self, *, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Fetch a list of records with pagination."""
        query = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, data: dict[str, Any]) -> ModelType:
        """Insert a new record into the database."""
        db_obj = self.model(**data)
        self.session.add(db_obj)
        await self.session.flush()  # populate ID and timestamps without committing transaction
        return db_obj

    async def update(self, db_obj: ModelType, data: dict[str, Any]) -> ModelType:
        """Update an existing record with new values."""
        for field, value in data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.session.add(db_obj)
        await self.session.flush()
        return db_obj

    async def delete(self, id: uuid.UUID) -> ModelType | None:
        """Delete a record by ID."""
        db_obj = await self.get(id)
        if db_obj:
            await self.session.delete(db_obj)
            await self.session.flush()
        return db_obj

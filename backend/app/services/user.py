from __future__ import annotations

import uuid
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate


class UserService:
    """Business logic layer for managing users."""

    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def get_user(self, user_id: uuid.UUID) -> User:
        """Retrieve a user by ID, raising an exception if not found."""
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found.")
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        """Retrieve a user by email, returning None if not found."""
        return await self.user_repo.get_by_email(email)

    async def create_user(self, user_in: UserCreate) -> User:
        """Register a new user, ensuring email uniqueness."""
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:
            raise ConflictError("A user with this email address already exists.")

        hashed_pwd = hash_password(user_in.password)
        user_data = {
            "email": user_in.email.lower(),
            "hashed_password": hashed_pwd,
            "is_active": True,
            "is_admin": False,
        }
        return await self.user_repo.create(user_data)

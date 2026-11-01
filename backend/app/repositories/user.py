from __future__ import annotations

import uuid
from datetime import datetime, UTC
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshToken, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """Fetch user by unique email address (case-insensitive)."""
        query = select(User).where(User.email == email.lower())
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    def _search_filter(self, q: str | None):
        if not q:
            return None
        like = f"%{q.strip().lower()}%"
        return or_(func.lower(User.email).like(like), func.lower(User.full_name).like(like))

    async def list_users(self, *, skip: int = 0, limit: int = 50, q: str | None = None) -> list[User]:
        """List users (admin), newest first, with optional email/name search."""
        query = select(User).order_by(User.created_at.desc())
        flt = self._search_filter(q)
        if flt is not None:
            query = query.where(flt)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_users(self, *, q: str | None = None) -> int:
        query = select(func.count()).select_from(User)
        flt = self._search_filter(q)
        if flt is not None:
            query = query.where(flt)
        result = await self.session.execute(query)
        return int(result.scalar_one())

    async def count_admins(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.is_admin.is_(True))
        )
        return int(result.scalar_one())

    async def get_by_verification_token(self, token: str) -> User | None:
        """Fetch user by email verification token."""
        query = select(User).where(User.email_verification_token == token)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_google_id(self, google_id: str) -> User | None:
        """Fetch user by their Google OAuth subject ID."""
        query = select(User).where(User.google_id == google_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_reset_token(self, token: str) -> User | None:
        """Fetch user by password reset token."""
        query = select(User).where(User.password_reset_token == token)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RefreshToken, session)

    async def get_by_token(self, token: str) -> RefreshToken | None:
        """Fetch refresh token record by token string."""
        query = select(RefreshToken).where(RefreshToken.token == token)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        """Fetch refresh token record by unique JTI."""
        query = select(RefreshToken).where(RefreshToken.jti == jti)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> None:
        """Revoke all refresh tokens for a user by setting revoked_at."""
        query = select(RefreshToken).where(
            RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
        )
        result = await self.session.execute(query)
        active_tokens = result.scalars().all()
        now = datetime.now(UTC)
        for token in active_tokens:
            token.revoked_at = now
            self.session.add(token)
        await self.session.flush()

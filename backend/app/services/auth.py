from __future__ import annotations

from datetime import datetime, timedelta, UTC
import uuid

from redis.asyncio import Redis

from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.repositories.user import RefreshTokenRepository, UserRepository
from app.schemas.user import Token


class AuthService:
    """Security and session orchestrator.

    Implements:
    * Password verification and token issuance
    * Strict Refresh Token Rotation (RTR)
    * Redis denylisting of invalidated JTIs (to prevent replay attacks)
    """

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
        redis: Redis,
    ) -> None:
        self.user_repo = user_repo
        self.token_repo = token_repo
        self.redis = redis

    async def authenticate(self, email: str, password: str) -> User:
        """Authenticate user credentials."""
        user = await self.user_repo.get_by_email(email)
        if not user or not user.is_active:
            raise AuthenticationError("Incorrect email or password.")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Incorrect email or password.")

        return user

    async def create_session(self, user_id: uuid.UUID) -> Token:
        """Create a new access and refresh token pair."""
        access_token = create_access_token(user_id)
        refresh_token_str, jti = create_refresh_token(user_id)

        # Persist refresh token metadata to database
        # 7 days lifetime
        expires_at = datetime.now(UTC) + timedelta(days=7)
        hashed_token = get_password_hash(refresh_token_str)
        await self.token_repo.create(
            {
                "user_id": user_id,
                "token": hashed_token,
                "jti": jti,
                "expires_at": expires_at,
            }
        )

        return Token(access_token=access_token, refresh_token=refresh_token_str)

    async def rotate_refresh_token(self, refresh_token: str) -> Token:
        """Rotate access and refresh token pair using strict refresh token rotation.

        If a refresh token is reused, we assume compromise and revoke all sessions
        for the user.
        """
        # 1. Decode token and enforce signature/expiry
        payload = decode_token(refresh_token, expected_type="refresh")
        jti = payload.get("jti")
        sub = payload.get("sub")

        if not jti or not sub:
            raise AuthenticationError("Invalid token payload.")

        user_id = uuid.UUID(sub)

        # 2. Check Redis denylist
        if await self.redis.get(f"denylist:jti:{jti}"):
            # Replay attack suspected! Revoke all tokens for the user as a safety measure.
            await self.token_repo.revoke_all_user_tokens(user_id)
            raise AuthenticationError("Token has been revoked.", code="token_revoked")

        # 3. Retrieve token metadata from database
        db_token = await self.token_repo.get_by_jti(jti)
        if not db_token:
            raise AuthenticationError("Refresh token not found.")

        if not verify_password(refresh_token, db_token.token):
            raise AuthenticationError("Invalid refresh token.")

        if db_token.revoked_at is not None:
            # Token was already used (database marker)
            await self.token_repo.revoke_all_user_tokens(user_id)
            raise AuthenticationError("Token has been revoked.", code="token_revoked")

        # 4. Invalidate the old refresh token (mark as revoked in DB, denylist in Redis)
        now = datetime.now(UTC)
        db_token.revoked_at = now
        self.token_repo.session.add(db_token)
        
        # Calculate remaining time to live for Redis denylist entry
        exp_timestamp = payload.get("exp")
        ttl = int(exp_timestamp - now.timestamp()) if exp_timestamp else 3600
        if ttl > 0:
            await self.redis.setex(f"denylist:jti:{jti}", ttl, "revoked")

        # 5. Issue a new token pair
        return await self.create_session(user_id)

    async def invalidate_session(self, refresh_token: str) -> None:
        """Revoke a single refresh token (Logout)."""
        payload = decode_token(refresh_token, expected_type="refresh")
        jti = payload.get("jti")
        if not jti:
            return

        db_token = await self.token_repo.get_by_jti(jti)
        if db_token and db_token.revoked_at is None:
            db_token.revoked_at = datetime.now(UTC)
            self.token_repo.session.add(db_token)

        now = datetime.now(UTC)
        exp_timestamp = payload.get("exp")
        ttl = int(exp_timestamp - now.timestamp()) if exp_timestamp else 3600
        if ttl > 0:
            await self.redis.setex(f"denylist:jti:{jti}", ttl, "revoked")

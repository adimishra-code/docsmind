"""Authentication service with login throttling and RTR."""
from __future__ import annotations

from datetime import datetime, timedelta, UTC
import hashlib
import uuid

from redis.asyncio import Redis

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User
from app.repositories.user import RefreshTokenRepository, UserRepository
from app.schemas.user import Token


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
        redis: Redis,
    ) -> None:
        self.user_repo = user_repo
        self.token_repo = token_repo
        self.redis = redis

    async def _check_login_attempts(self, email: str) -> None:
        cache_key = "login_attempts:{0}".format(email)
        attempts = await self.redis.get(cache_key)
        
        if attempts and int(attempts) >= settings.LOGIN_MAX_ATTEMPTS:
            lockout_key = "login_lockout:{0}".format(email)
            lockout_until = await self.redis.get(lockout_key)
            
            if lockout_until:
                lockout_time = int(lockout_until)
                remaining = lockout_time - int(datetime.now(UTC).timestamp())
                if remaining > 0:
                    raise AuthenticationError(
                        "Too many login attempts. Try again in {0} minutes.".format(remaining // 60),
                        code="account_locked",
                    )
                else:
                    await self.redis.delete(cache_key)
                    await self.redis.delete(lockout_key)
    
    async def _record_failed_login(self, email: str) -> None:
        cache_key = "login_attempts:{0}".format(email)
        lockout_key = "login_lockout:{0}".format(email)
        
        attempts = await self.redis.incr(cache_key)
        await self.redis.expire(cache_key, 86400)
        
        if attempts >= settings.LOGIN_MAX_ATTEMPTS:
            lockout_duration = settings.LOGIN_LOCKOUT_MINUTES * 60
            await self.redis.setex(lockout_key, lockout_duration, str(int(datetime.now(UTC).timestamp()) + lockout_duration))
            await self.redis.delete(cache_key)

    async def _clear_failed_logins(self, email: str) -> None:
        cache_key = "login_attempts:{0}".format(email)
        lockout_key = "login_lockout:{0}".format(email)
        await self.redis.delete(cache_key)
        await self.redis.delete(lockout_key)

    async def _log_audit(
        self,
        user_id: uuid.UUID | None,
        action: str,
        status: str,
        detail: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        from app.models.audit import AuditLog
        log = AuditLog(
            user_id=user_id,
            action=action,
            status=status,
            detail=detail,
            ip_address=ip_address,
        )
        self.token_repo.session.add(log)
        await self.token_repo.session.flush()

    async def authenticate(self, email: str, password: str) -> User:
        await self._check_login_attempts(email)

        user = await self.user_repo.get_by_email(email.lower())
        if not user or not user.is_active:
            if user:
                await self._record_failed_login(email.lower())
                await self._log_audit(user.id, "login", "failure", "User not found or inactive")
            raise AuthenticationError("Incorrect email or password.")

        if not verify_password(password, user.hashed_password or ""):
            await self._record_failed_login(email.lower())
            await self._log_audit(user.id, "login", "failure", "Invalid password")
            raise AuthenticationError("Incorrect email or password.")

        # Require email verification (Google users are auto-verified)
        if not user.email_verified:
            raise AuthenticationError(
                "Please verify your email address before logging in. "
                "Check your inbox or request a new verification email.",
                code="email_not_verified",
            )

        await self._clear_failed_logins(email.lower())
        await self._log_audit(user.id, "login", "success")
        return user


    async def create_session(self, user_id: uuid.UUID) -> Token:
        access_token = create_access_token(user_id)
        refresh_token_str, jti = create_refresh_token(user_id)

        expires_at = datetime.now(UTC) + timedelta(days=7)
        hashed_token = hashlib.sha256(refresh_token_str.encode()).hexdigest()
        await self.token_repo.create(
            {"user_id": user_id, "token": hashed_token, "jti": jti, "expires_at": expires_at}
        )

        await self._log_audit(user_id, "token_issued", "success", detail="Access+refresh token pair issued")
        return Token(access_token=access_token, refresh_token=refresh_token_str)

    async def rotate_refresh_token(self, refresh_token: str) -> Token:
        payload = decode_token(refresh_token, expected_type="refresh")
        jti = payload.get("jti")
        sub = payload.get("sub")

        if not jti or not sub:
            raise AuthenticationError("Invalid token payload.")

        user_id = uuid.UUID(sub)

        if await self.redis.get("denylist:jti:{0}".format(jti)):
            await self.token_repo.revoke_all_user_tokens(user_id)
            await self._log_audit(user_id, "token_replay", "blocked", detail="Replay detected for JTI: {0}".format(jti))
            raise AuthenticationError("Token has been revoked.", code="token_revoked")

        db_token = await self.token_repo.get_by_jti(jti)
        if not db_token:
            raise AuthenticationError("Refresh token not found.")

        if hashlib.sha256(refresh_token.encode()).hexdigest() != db_token.token:
            raise AuthenticationError("Invalid refresh token.")

        if db_token.revoked_at is not None:
            await self.token_repo.revoke_all_user_tokens(user_id)
            await self._log_audit(user_id, "token_reuse", "blocked", detail="Revoked token reused, all sessions revoked")
            raise AuthenticationError("Token has been revoked.", code="token_revoked")

        now = datetime.now(UTC)
        db_token.revoked_at = now
        self.token_repo.session.add(db_token)

        exp_timestamp = payload.get("exp")
        ttl = int(exp_timestamp - now.timestamp()) if exp_timestamp else 3600
        if ttl > 0:
            await self.redis.setex("denylist:jti:{0}".format(jti), ttl, "revoked")

        await self._log_audit(user_id, "token_rotation", "success")
        return await self.create_session(user_id)

    async def invalidate_session(self, refresh_token: str) -> None:
        payload = decode_token(refresh_token, expected_type="refresh")
        jti = payload.get("jti")
        sub = payload.get("sub")
        if not jti:
            return

        db_token = await self.token_repo.get_by_jti(jti)
        user_id = uuid.UUID(sub) if sub else None
        if db_token and db_token.revoked_at is None:
            db_token.revoked_at = datetime.now(UTC)
            self.token_repo.session.add(db_token)

        now = datetime.now(UTC)
        exp_timestamp = payload.get("exp")
        ttl = int(exp_timestamp - now.timestamp()) if exp_timestamp else 3600
        if ttl > 0:
            await self.redis.setex("denylist:jti:{0}".format(jti), ttl, "revoked")

        await self._log_audit(user_id, "logout", "success")
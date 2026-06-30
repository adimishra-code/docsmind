from __future__ import annotations

from collections.abc import AsyncGenerator
import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_token
from app.db.redis import get_redis
from app.db.session import get_db
from app.models.user import User
from app.repositories.chat import ChatRepository, MessageRepository
from app.repositories.document import DocumentRepository
from app.repositories.user import RefreshTokenRepository, UserRepository
from app.services.auth import AuthService
from app.services.user import UserService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,  # manually handle errors to raise custom AuthenticationError
)

# ---- DB & Cache Dependencies ----
DBDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]

# ---- Repository Dependencies ----
async def get_user_repository(db: DBDep) -> UserRepository:
    return UserRepository(db)

async def get_token_repository(db: DBDep) -> RefreshTokenRepository:
    return RefreshTokenRepository(db)

async def get_document_repository(db: DBDep) -> DocumentRepository:
    return DocumentRepository(db)

async def get_chat_repository(db: DBDep) -> ChatRepository:
    return ChatRepository(db)

async def get_message_repository(db: DBDep) -> MessageRepository:
    return MessageRepository(db)

UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
TokenRepoDep = Annotated[RefreshTokenRepository, Depends(get_token_repository)]
DocRepoDep = Annotated[DocumentRepository, Depends(get_document_repository)]
ChatRepoDep = Annotated[ChatRepository, Depends(get_chat_repository)]
MessageRepoDep = Annotated[MessageRepository, Depends(get_message_repository)]

# ---- Service Dependencies ----
async def get_user_service(user_repo: UserRepoDep) -> UserService:
    return UserService(user_repo)

async def get_auth_service(
    user_repo: UserRepoDep,
    token_repo: TokenRepoDep,
    redis: RedisDep,
) -> AuthService:
    return AuthService(user_repo, token_repo, redis)

UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

# ---- Security & Authentication Dependencies ----
async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    user_repo: UserRepoDep,
) -> User:
    """Fetch the authenticated user from the request's Authorization header."""
    if not token:
        raise AuthenticationError("Not authenticated.", code="not_authenticated")

    payload = decode_token(token, expected_type="access")
    sub = payload.get("sub")
    if not sub:
        raise AuthenticationError("Invalid access token.")

    try:
        user_uuid = uuid.UUID(sub)
    except ValueError as exc:
        raise AuthenticationError("Invalid token subject.") from exc

    user = await user_repo.get(user_uuid)
    if not user:
        raise AuthenticationError("User not found.")
    if not user.is_active:
        raise AuthenticationError("User account is disabled.", code="user_disabled")

    return user

CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_current_active_user(
    current_user: CurrentUserDep,
) -> User:
    """Ensure the user is active."""
    if not current_user.is_active:
        raise PermissionDeniedError("Inactive user.")
    return current_user


async def get_current_admin(
    current_user: CurrentUserDep,
) -> User:
    """Enforce administrator permissions."""
    if not current_user.is_admin:
        raise PermissionDeniedError("Administrative privileges required.")
    return current_user

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select

from app.api.deps import UserRepoDep, get_current_admin
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.audit import AuditLog
from app.models.chat import ChatSession
from app.models.document import Document
from app.models.user import User
from app.schemas.user import (
    AdminRoleRequest,
    AdminStatsResponse,
    AdminUserListResponse,
    UserResponse,
)

logger = get_logger(__name__)

router = APIRouter()

# Every route in this router requires an authenticated admin.
AdminDep = Annotated[User, Depends(get_current_admin)]


async def _record_audit(repo: UserRepoDep, actor: User, action: str, target_email: str) -> None:
    repo.session.add(
        AuditLog(
            user_id=actor.id,
            action=action,
            status="success",
            detail=target_email,
            extra={"actor_email": actor.email},
        )
    )


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List all users (admin)",
)
async def list_users(
    _admin: AdminDep,
    user_repo: UserRepoDep,
    q: str | None = None,
    skip: int = 0,
    limit: int = Query(default=50, le=200),
) -> dict:
    """Return a paginated list of users, optionally filtered by email/name."""
    items = await user_repo.list_users(skip=skip, limit=limit, q=q)
    total = await user_repo.count_users(q=q)
    page = (skip // limit) + 1 if limit else 1
    total_pages = max(1, -(-total // limit)) if limit else 1
    return {"items": items, "total": total, "page": page, "page_size": limit, "total_pages": total_pages}


@router.post(
    "/users/promote",
    response_model=UserResponse,
    summary="Grant admin to a user by email",
)
async def promote_user(
    body: AdminRoleRequest,
    admin: AdminDep,
    user_repo: UserRepoDep,
) -> User:
    """Promote the user with the given email to administrator."""
    target = await user_repo.get_by_email(str(body.email))
    if not target:
        raise NotFoundError(f"No user found with email {body.email}.")

    if not target.is_admin:
        target.is_admin = True
        user_repo.session.add(target)
        await _record_audit(user_repo, admin, "admin.promote", target.email)

    await user_repo.session.commit()
    logger.info("User promoted to admin", target=target.email, actor=admin.email)
    return target


@router.post(
    "/users/demote",
    response_model=UserResponse,
    summary="Revoke admin from a user by email",
)
async def demote_user(
    body: AdminRoleRequest,
    admin: AdminDep,
    user_repo: UserRepoDep,
) -> User:
    """Revoke administrator rights from the user with the given email."""
    target = await user_repo.get_by_email(str(body.email))
    if not target:
        raise NotFoundError(f"No user found with email {body.email}.")

    if target.id == admin.id:
        raise ValidationError("You cannot revoke your own admin access.")

    if target.is_admin:
        # Never leave the system with zero admins.
        if await user_repo.count_admins() <= 1:
            raise ValidationError("Cannot demote the last remaining administrator.")
        target.is_admin = False
        user_repo.session.add(target)
        await _record_audit(user_repo, admin, "admin.demote", target.email)

    await user_repo.session.commit()
    logger.info("User demoted from admin", target=target.email, actor=admin.email)
    return target


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Platform-wide counts (admin)",
)
async def admin_stats(
    _admin: AdminDep,
    user_repo: UserRepoDep,
) -> dict:
    """Real, DB-backed counts for the admin overview."""
    session = user_repo.session
    total_users = await user_repo.count_users()
    total_admins = await user_repo.count_admins()
    active_users = int(
        (await session.execute(
            select(func.count()).select_from(User).where(User.is_active.is_(True))
        )).scalar_one()
    )
    total_documents = int(
        (await session.execute(select(func.count()).select_from(Document))).scalar_one()
    )
    total_chats = int(
        (await session.execute(select(func.count()).select_from(ChatSession))).scalar_one()
    )
    return {
        "total_users": total_users,
        "total_admins": total_admins,
        "active_users": active_users,
        "total_documents": total_documents,
        "total_chats": total_chats,
    }

from __future__ import annotations

from datetime import datetime
import uuid
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: uuid.UUID
    full_name: str | None
    avatar_url: str | None
    is_active: bool
    is_admin: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    sub: str
    type: str
    jti: str
    iat: datetime
    exp: datetime


class MessageResponse(BaseModel):
    message: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class GoogleOAuthResponse(BaseModel):
    """Response for when Google OAuth user info is fetched."""
    id: str
    email: EmailStr
    name: str | None = None
    picture: str | None = None
    verified_email: bool = False


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)


# ---- Admin ----

class AdminUserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


class AdminRoleRequest(BaseModel):
    """Promote/demote a user identified by email (as typed in the admin UI)."""
    email: EmailStr


class AdminStatsResponse(BaseModel):
    total_users: int
    total_admins: int
    active_users: int
    total_documents: int
    total_chats: int

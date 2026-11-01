from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
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
        """Register a new user with email+password, generates a verification token."""
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:
            raise ConflictError("A user with this email address already exists.")

        hashed_pwd = hash_password(user_in.password)
        verification_token = secrets.token_urlsafe(48)

        user_data = {
            "email": user_in.email.lower(),
            "hashed_password": hashed_pwd,
            "full_name": getattr(user_in, "full_name", None),
            "is_active": True,
            "is_admin": False,
            "email_verified": not settings.REQUIRE_EMAIL_VERIFICATION or settings.ENVIRONMENT == "development",
            "email_verification_token": verification_token,
            "email_verification_sent_at": datetime.now(UTC),
        }
        return await self.user_repo.create(user_data)

    async def verify_email_token(self, token: str) -> User:
        """Verify an email verification token, mark user as verified."""
        user = await self.user_repo.get_by_verification_token(token)
        if not user:
            raise NotFoundError("Invalid or expired verification token.")

        # Check token expiry (24 hours)
        if user.email_verification_sent_at:
            expiry = user.email_verification_sent_at + timedelta(
                hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
            )
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=UTC)
            if datetime.now(UTC) > expiry:
                raise ValidationError("Verification link has expired. Please request a new one.")

        user.email_verified = True
        user.email_verification_token = None
        user.email_verification_sent_at = None
        self.user_repo.session.add(user)
        return user

    async def resend_verification_email(self, email: str) -> User:
        """Regenerate and resend a verification email."""
        user = await self.user_repo.get_by_email(email.lower())
        if not user:
            raise NotFoundError("No account found with this email.")
        if user.email_verified:
            raise ConflictError("This email is already verified.")

        # Rate-limit: don't resend if sent within the last 60 seconds
        if user.email_verification_sent_at:
            sent_at = user.email_verification_sent_at
            if sent_at.tzinfo is None:
                sent_at = sent_at.replace(tzinfo=UTC)
            since = datetime.now(UTC) - sent_at
            if since.total_seconds() < 60:
                raise ValidationError("Please wait before requesting another verification email.")

        new_token = secrets.token_urlsafe(48)
        user.email_verification_token = new_token
        user.email_verification_sent_at = datetime.now(UTC)
        self.user_repo.session.add(user)
        return user

    async def get_or_create_google_user(
        self,
        google_id: str,
        email: str,
        full_name: str | None,
        avatar_url: str | None,
    ) -> tuple[User, bool]:
        """Find or create a user from Google OAuth profile.
        
        Returns (user, is_new_user).
        """
        # First, try to find by google_id
        user = await self.user_repo.get_by_google_id(google_id)
        if user:
            # Update avatar/name if changed
            updated = False
            if full_name and user.full_name != full_name:
                user.full_name = full_name
                updated = True
            if avatar_url and user.avatar_url != avatar_url:
                user.avatar_url = avatar_url
                updated = True
            if updated:
                self.user_repo.session.add(user)
            return user, False

        # Try to find by email (link existing account)
        user = await self.user_repo.get_by_email(email.lower())
        if user:
            # Link google_id to existing account and verify email
            user.google_id = google_id
            user.email_verified = True
            if full_name and not user.full_name:
                user.full_name = full_name
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
            self.user_repo.session.add(user)
            return user, False

        # Create a brand new Google user
        user_data = {
            "email": email.lower(),
            "hashed_password": None,  # No password for Google-only users
            "full_name": full_name,
            "avatar_url": avatar_url,
            "google_id": google_id,
            "is_active": True,
            "is_admin": False,
            "email_verified": True,  # Google accounts are pre-verified
            "email_verification_token": None,
            "email_verification_sent_at": None,
        }
        user = await self.user_repo.create(user_data)
        return user, True

    async def request_password_reset(self, email: str) -> User | None:
        """Generate a password reset token. Returns None silently if user not found (security best practice)."""
        user = await self.user_repo.get_by_email(email.lower())
        if not user or not user.is_active:
            return None  # Do not reveal whether email exists

        # Rate-limit: don't resend within 60 seconds
        if user.password_reset_sent_at:
            sent_at = user.password_reset_sent_at
            if sent_at.tzinfo is None:
                sent_at = sent_at.replace(tzinfo=UTC)
            since = datetime.now(UTC) - sent_at
            if since.total_seconds() < 60:
                raise ValidationError("Please wait before requesting another reset email.")

        token = secrets.token_urlsafe(48)
        user.password_reset_token = token
        user.password_reset_sent_at = datetime.now(UTC)
        self.user_repo.session.add(user)
        return user

    async def verify_reset_token(self, token: str) -> User:
        """Validate a password reset token without consuming it. Raises on invalid/expired."""
        user = await self.user_repo.get_by_reset_token(token)
        if not user:
            raise ValidationError("Invalid or expired password reset link.", code="invalid_token")

        # Tokens expire after 1 hour
        if user.password_reset_sent_at:
            expiry = user.password_reset_sent_at + timedelta(hours=1)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=UTC)
            if datetime.now(UTC) > expiry:
                raise ValidationError("This reset link has expired. Please request a new one.", code="token_expired")

        return user

    async def reset_password(self, token: str, new_password: str) -> User:
        """Consume the reset token and update the user's password."""
        user = await self.verify_reset_token(token)

        user.hashed_password = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_sent_at = None
        self.user_repo.session.add(user)
        return user

    async def update_profile(self, user_id: uuid.UUID, full_name: str | None) -> User:
        """Update user profile fields."""
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found.")

        if full_name is not None:
            user.full_name = full_name.strip() or None
        self.user_repo.session.add(user)
        return user


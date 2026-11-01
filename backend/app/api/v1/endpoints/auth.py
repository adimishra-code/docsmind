from __future__ import annotations

import urllib.parse

import httpx
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import RedirectResponse

from app.api.deps import AuthServiceDep, CurrentUserDep, DocRepoDep, UserServiceDep
from app.api.middleware.throttle import RegisterThrottle
from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger
from app.schemas.user import (
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    ProfileUpdateRequest,
    ResendVerificationRequest,
    Token,
    TokenRefreshRequest,
    UserCreate,
    UserResponse,
)
from app.services.email import send_verification_email, send_welcome_email, send_password_reset_email

router = APIRouter()
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    _: RegisterThrottle,
    user_in: UserCreate,
    user_service: UserServiceDep,
) -> MessageResponse:
    """Create a new user account. Sends an email verification link."""
    user = await user_service.create_user(user_in)
    session = user_service.user_repo.session
    await session.flush()

    # Send verification email (non-blocking — failure won't abort registration)
    if user.email_verification_token:
        await send_verification_email(user.email, user.email_verification_token)

    await session.commit()
    return MessageResponse(
        message="Registration successful! Please check your email to verify your account."
    )


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------

@router.get(
    "/verify-email",
    summary="Verify email via token link",
)
async def verify_email(
    token: str,
    user_service: UserServiceDep,
) -> RedirectResponse:
    """Verify user's email. Called when user clicks the link in the email."""
    try:
        user = await user_service.verify_email_token(token)
        session = user_service.user_repo.session
        await session.commit()
        redirect_url = f"{settings.FRONTEND_URL}/login?verified=true"
    except Exception:
        redirect_url = f"{settings.FRONTEND_URL}/login?error=invalid_token"

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Resend email verification link",
)
async def resend_verification(
    body: ResendVerificationRequest,
    user_service: UserServiceDep,
) -> MessageResponse:
    """Resend email verification to the given email address."""
    user = await user_service.resend_verification_email(body.email)
    session = user_service.user_repo.session
    await session.flush()

    if user.email_verification_token:
        await send_verification_email(user.email, user.email_verification_token)

    await session.commit()
    return MessageResponse(message="Verification email resent. Please check your inbox.")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User authentication login",
)
async def login(
    credentials: LoginRequest,
    auth_service: AuthServiceDep,
) -> Token:
    """Authenticate email+password and issue Access + Refresh tokens.
    Requires email to be verified first.
    """
    user = await auth_service.authenticate(
        email=credentials.email, password=credentials.password
    )
    session = auth_service.user_repo.session

    # Bootstrap: emails listed in ADMIN_EMAILS become admins on login. This
    # seeds the first administrator; subsequent admins are promoted in-app.
    if not user.is_admin and user.email.lower() in settings.admin_emails:
        user.is_admin = True
        session.add(user)

    token = await auth_service.create_session(user.id)
    await session.commit()
    return token


# ---------------------------------------------------------------------------
# Token Rotation & Logout
# ---------------------------------------------------------------------------

@router.post(
    "/refresh",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Rotate tokens via Refresh Token Rotation",
)
async def refresh_tokens(
    body: TokenRefreshRequest,
    auth_service: AuthServiceDep,
) -> Token:
    """Rotate the refresh token, invalidating the previous one to prevent replay attacks."""
    session = auth_service.user_repo.session
    token = await auth_service.rotate_refresh_token(body.refresh_token)
    await session.commit()
    return token


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Invalidate user session",
)
async def logout(
    body: TokenRefreshRequest,
    auth_service: AuthServiceDep,
) -> Response:
    """Revoke a refresh token, adding it to the denylist to prevent reuse."""
    session = auth_service.user_repo.session
    await auth_service.invalidate_session(body.refresh_token)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user details",
)
async def get_me(current_user: CurrentUserDep) -> UserResponse:
    """Retrieve details for the currently logged-in user."""
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
)
async def update_me(
    body: ProfileUpdateRequest,
    current_user: CurrentUserDep,
    user_service: UserServiceDep,
) -> UserResponse:
    """Update the current user's profile (display name)."""
    user = await user_service.update_profile(current_user.id, body.full_name)
    await user_service.user_repo.session.commit()
    return user


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete current user account",
)
async def delete_me(
    current_user: CurrentUserDep,
    user_service: UserServiceDep,
    doc_repo: DocRepoDep,
) -> Response:
    """Permanently delete the current account and all associated data.

    Database rows (documents, chunks, chat sessions, messages, refresh tokens)
    cascade from the ``users`` row. External state — object-storage binaries and
    Qdrant/BM25 indexes — is cleaned up best-effort first, since the user has
    explicitly requested erasure and residual index entries must not survive.
    """
    from app.db.redis import redis_client
    from app.services.rag.bm25_manager import BM25IndexManager
    from app.services.rag.vector_store import QdrantAdapter
    from app.services.storage import get_storage_backend

    user_id = current_user.id
    storage = None
    vector_store = None

    skip = 0
    had_documents = False
    while True:
        documents, _total = await doc_repo.get_multi_by_user(user_id, skip=skip, limit=200)
        if not documents:
            break
        if storage is None:
            storage = get_storage_backend()
            vector_store = QdrantAdapter()
        had_documents = True
        for doc in documents:
            try:
                await storage.delete(doc.storage_path)
            except Exception:
                logger.warning("Storage cleanup failed during account deletion", document_id=str(doc.id))
            try:
                await vector_store.delete_by_document("document_chunks", doc.id, user_id)
            except Exception:
                logger.warning("Vector cleanup failed during account deletion", document_id=str(doc.id))
        if len(documents) < 200:
            break
        skip += 200

    if had_documents:
        try:
            await BM25IndexManager(redis_client).invalidate(user_id)
        except Exception:
            logger.warning("BM25 invalidation failed during account deletion", user_id=str(user_id))

    # Cascades to documents, chunks, chats, messages and refresh tokens.
    await user_service.user_repo.delete(user_id)
    await user_service.user_repo.session.commit()

    logger.info("User account deleted", user_id=str(user_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------

@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a password reset email",
)
async def forgot_password(
    body: PasswordResetRequest,
    user_service: UserServiceDep,
) -> MessageResponse:
    """Send a password reset link to the given email if an account exists.
    Always returns the same message to prevent user enumeration.
    """
    user = await user_service.request_password_reset(body.email)
    session = user_service.user_repo.session
    await session.flush()

    if user and user.password_reset_token:
        await send_password_reset_email(user.email, user.password_reset_token)

    await session.commit()
    return MessageResponse(
        message="If an account with that email exists, you'll receive a password reset link shortly."
    )


@router.get(
    "/reset-password/verify",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify a password reset token",
)
async def verify_reset_token(
    token: str,
    user_service: UserServiceDep,
) -> MessageResponse:
    """Validate that a password reset token is still valid (not expired or already used)."""
    await user_service.verify_reset_token(token)
    return MessageResponse(message="Token is valid.")


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password using a valid token",
)
async def reset_password(
    body: PasswordResetConfirmRequest,
    user_service: UserServiceDep,
) -> MessageResponse:
    """Consume the reset token and set the new password."""
    await user_service.reset_password(body.token, body.new_password)
    session = user_service.user_repo.session
    await session.commit()
    return MessageResponse(message="Your password has been reset successfully. You can now log in.")


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------

@router.get(
    "/google",
    summary="Initiate Google OAuth2 login",
)
async def google_login() -> RedirectResponse:
    """Redirect user to Google's OAuth2 consent screen."""
    if not settings.google_oauth_enabled:
        redirect_url = f"{settings.FRONTEND_URL}/login?error=google_oauth_not_configured"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return RedirectResponse(url=google_auth_url)


@router.get(
    "/google/callback",
    summary="Google OAuth2 callback handler",
)
async def google_callback(
    code: str,
    user_service: UserServiceDep,
    auth_service: AuthServiceDep,
    error: str | None = None,
) -> RedirectResponse:
    """Exchange Google OAuth code for user profile, then issue JWT tokens."""
    if error:
        redirect_url = f"{settings.FRONTEND_URL}/login?error=google_oauth_cancelled"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    if not settings.google_oauth_enabled:
        redirect_url = f"{settings.FRONTEND_URL}/login?error=oauth_not_configured"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    try:
        async with httpx.AsyncClient() as client:
            # Exchange code for token
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                timeout=10,
            )
            token_response.raise_for_status()
            token_data = token_response.json()

            # Fetch Google user profile
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
                timeout=10,
            )
            userinfo_response.raise_for_status()
            profile = userinfo_response.json()

        google_id = profile.get("id")
        email = profile.get("email")
        full_name = profile.get("name")
        avatar_url = profile.get("picture")

        if not google_id or not email:
            raise ValueError("Incomplete Google profile received")

        # Get or create user
        user, _is_new = await user_service.get_or_create_google_user(
            google_id=google_id,
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
        )

        session = user_service.user_repo.session
        await session.flush()

        # Issue tokens
        token = await auth_service.create_session(user.id)
        await session.commit()

        # Redirect to frontend with tokens encoded in URL fragment (SPA approach)
        params = urllib.parse.urlencode({
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
        })
        redirect_url = f"{settings.FRONTEND_URL}/oauth/callback?{params}"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    except Exception as exc:
        logger.error("Google OAuth error", error=str(exc))
        redirect_url = f"{settings.FRONTEND_URL}/login?error=google_oauth_failed"
        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

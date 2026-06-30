from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import AuthServiceDep, CurrentUserDep, UserServiceDep
from app.schemas.user import Token, TokenRefreshRequest, UserCreate, UserResponse

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    user_in: UserCreate,
    user_service: UserServiceDep,
) -> UserResponse:
    """Create a new user account with unique email address."""
    user = await user_service.create_user(user_in)
    # Return User model which maps cleanly to UserResponse schema
    return user


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User authentication login",
)
async def login(
    credentials: UserCreate,  # custom JSON login schema (reusing UserCreate email/password)
    auth_service: AuthServiceDep,
) -> Token:
    """Authenticate email and password and issue Access and Refresh tokens."""
    user = await auth_service.authenticate(
        email=credentials.email, password=credentials.password
    )
    # We must commit or let FastAPI session commit the transactional updates
    # The get_db generator rolls back on exception, commits on success or we can flush/commit.
    # In FastAPI, we can commit at the service level, or let the router commit.
    # Let's commit at the endpoint level or let session handle it.
    # In auth service, we performed flushes; we will commit at the end of the request.
    session = auth_service.user_repo.session
    token = await auth_service.create_session(user.id)
    await session.commit()
    return token


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
) -> None:
    """Revoke a refresh token, adding it to the denylist to prevent reuse."""
    session = auth_service.user_repo.session
    await auth_service.invalidate_session(body.refresh_token)
    await session.commit()


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user details",
)
async def get_me(current_user: CurrentUserDep) -> UserResponse:
    """Retrieve details for the currently logged-in user."""
    return current_user

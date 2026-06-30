from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient) -> None:
    """Test successful user registration."""
    response = await client.post(
        "/auth/register",
        json={"email": "newuser@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_user_validation_error(client: AsyncClient) -> None:
    """Test registration validation for invalid passwords and emails."""
    # Short password
    response = await client.post(
        "/auth/register",
        json={"email": "shortpwd@example.com", "password": "short"},
    )
    assert response.status_code == 422
    assert "Validation failed" in response.json()["error"]

    # Invalid email
    response = await client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "securepassword123"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_user_duplicate_email(client: AsyncClient) -> None:
    """Test that duplicate registrations fail with 409 Conflict."""
    payload = {"email": "duplicate@example.com", "password": "securepassword123"}

    # First registration
    response1 = await client.post("/auth/register", json=payload)
    assert response1.status_code == 201

    # Second registration with same email
    response2 = await client.post("/auth/register", json=payload)
    assert response2.status_code == 409
    assert response2.json()["code"] == "conflict"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    """Test successful login and JWT issuing."""
    # Register first
    await client.post(
        "/auth/register",
        json={"email": "loginuser@example.com", "password": "securepassword123"},
    )

    # Login
    response = await client.post(
        "/auth/login",
        json={"email": "loginuser@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient) -> None:
    """Test login with incorrect password or email."""
    # Register first
    await client.post(
        "/auth/register",
        json={"email": "wrongpwd@example.com", "password": "securepassword123"},
    )

    # Wrong password
    response = await client.post(
        "/auth/login",
        json={"email": "wrongpwd@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "authentication_error"

    # Non-existent email
    response = await client.post(
        "/auth/login",
        json={"email": "nonexistent@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_me(client: AsyncClient) -> None:
    """Test retrieval of current user profile with active token."""
    await client.post(
        "/auth/register",
        json={"email": "me@example.com", "password": "securepassword123"},
    )
    login_resp = await client.post(
        "/auth/login",
        json={"email": "me@example.com", "password": "securepassword123"},
    )
    access_token = login_resp.json()["access_token"]

    # Authenticated request
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"

    # Unauthenticated request
    response_unauth = await client.get("/auth/me")
    assert response_unauth.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_replay_protection(client: AsyncClient) -> None:
    """Test refresh token rotation and suspect replay attack handling (RTR)."""
    # 1. Register & Login
    await client.post(
        "/auth/register",
        json={"email": "rtr@example.com", "password": "securepassword123"},
    )
    login_resp = await client.post(
        "/auth/login",
        json={"email": "rtr@example.com", "password": "securepassword123"},
    )
    tokens = login_resp.json()
    first_refresh = tokens["refresh_token"]

    # 2. Use refresh token once (should succeed and give new tokens)
    refresh_resp1 = await client.post(
        "/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert refresh_resp1.status_code == 200
    new_tokens = refresh_resp1.json()
    second_refresh = new_tokens["refresh_token"]
    new_access = new_tokens["access_token"]
    assert second_refresh != first_refresh

    # 3. Access endpoint using new access token (should succeed)
    headers = {"Authorization": f"Bearer {new_access}"}
    me_resp = await client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 200

    # 4. Attempt to REPLAY the first refresh token (should be rejected)
    replay_resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert replay_resp.status_code == 401
    assert replay_resp.json()["code"] == "token_revoked"

    # 5. Verify that the second refresh token is now ALSO revoked due to security breach actions
    revoked_resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": second_refresh},
    )
    assert revoked_resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(client: AsyncClient) -> None:
    """Test logging out (invalidating refresh token)."""
    await client.post(
        "/auth/register",
        json={"email": "logout@example.com", "password": "securepassword123"},
    )
    login_resp = await client.post(
        "/auth/login",
        json={"email": "logout@example.com", "password": "securepassword123"},
    )
    tokens = login_resp.json()
    refresh_token = tokens["refresh_token"]

    # Logout
    logout_resp = await client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 204

    # Verify refresh token is unusable
    refresh_resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 401

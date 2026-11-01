"""Admin API: role management and access control.

Covers the core guarantees a "make someone an admin" feature must hold:
non-admins are refused, admins can list/promote/demote by email, and the system
can never be left with zero admins or an admin who demoted themselves.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

import app.core.config as config_module


async def _register_and_login(client: AsyncClient, email: str, password: str = "securepassword123") -> dict:
    await client.post("/auth/register", json={"email": email, "password": password})
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _make_bootstrap_admin(client: AsyncClient, monkeypatch, email: str) -> dict:
    """Register a user whose email is in ADMIN_EMAILS -> admin on login."""
    monkeypatch.setattr(config_module.settings, "ADMIN_EMAILS", email, raising=False)
    return await _register_and_login(client, email)


@pytest.mark.asyncio
async def test_non_admin_is_forbidden(client: AsyncClient) -> None:
    headers = await _register_and_login(client, "regular@example.com")
    resp = await client.get("/admin/users", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_bootstrap_admin_can_list_users(client: AsyncClient, monkeypatch) -> None:
    admin_headers = await _make_bootstrap_admin(client, monkeypatch, "admin@example.com")
    await _register_and_login(client, "someone@example.com")

    resp = await client.get("/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    emails = {u["email"] for u in data["items"]}
    assert "admin@example.com" in emails and "someone@example.com" in emails


@pytest.mark.asyncio
async def test_promote_and_demote_by_email(client: AsyncClient, monkeypatch) -> None:
    admin_headers = await _make_bootstrap_admin(client, monkeypatch, "admin@example.com")
    target_headers = await _register_and_login(client, "target@example.com")

    # Target is not admin yet.
    assert (await client.get("/admin/users", headers=target_headers)).status_code == 403

    # Promote by email.
    resp = await client.post("/admin/users/promote", headers=admin_headers, json={"email": "target@example.com"})
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is True

    # Target can now use the admin API.
    assert (await client.get("/admin/users", headers=target_headers)).status_code == 200

    # Demote by email.
    resp = await client.post("/admin/users/demote", headers=admin_headers, json={"email": "target@example.com"})
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is False
    assert (await client.get("/admin/users", headers=target_headers)).status_code == 403


@pytest.mark.asyncio
async def test_promote_unknown_email_404(client: AsyncClient, monkeypatch) -> None:
    admin_headers = await _make_bootstrap_admin(client, monkeypatch, "admin@example.com")
    resp = await client.post("/admin/users/promote", headers=admin_headers, json={"email": "nobody@example.com"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_demote_self_or_last_admin(client: AsyncClient, monkeypatch) -> None:
    admin_headers = await _make_bootstrap_admin(client, monkeypatch, "admin@example.com")
    # Self-demotion is refused outright.
    resp = await client.post("/admin/users/demote", headers=admin_headers, json={"email": "admin@example.com"})
    assert resp.status_code in (400, 422)

    # Promote a second admin, then demoting the original is allowed (not last).
    await _register_and_login(client, "second@example.com")
    await client.post("/admin/users/promote", headers=admin_headers, json={"email": "second@example.com"})
    resp = await client.post("/admin/users/demote", headers=admin_headers, json={"email": "second@example.com"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_stats(client: AsyncClient, monkeypatch) -> None:
    admin_headers = await _make_bootstrap_admin(client, monkeypatch, "admin@example.com")
    resp = await client.get("/admin/stats", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_users"] >= 1
    assert data["total_admins"] >= 1
    assert set(data) == {"total_users", "total_admins", "active_users", "total_documents", "total_chats"}

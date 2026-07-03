from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> tuple[str, uuid.UUID]:
    await client.post("/auth/register", json={"email": email, "password": "securepassword123"})
    login = await client.post("/auth/login", json={"email": email, "password": "securepassword123"})
    token = login.json()["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, uuid.UUID(me.json()["id"])


async def _insert_document(user_id: uuid.UUID, status: str) -> uuid.UUID:
    from app.db.session import AsyncSessionLocal
    from app.models.document import Document

    doc_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        session.add(
            Document(
                id=doc_id,
                user_id=user_id,
                filename="broken.pdf",
                file_type=".pdf",
                storage_path=f"{user_id}/broken.pdf",
                file_size=1234,
                status=status,
                error_message="boom" if status == "failed" else None,
            )
        )
        await session.commit()
    return doc_id


@pytest.mark.asyncio
async def test_reprocess_failed_document(client: AsyncClient, monkeypatch) -> None:
    """A failed document can be re-queued: status resets to pending and the task re-dispatches."""
    token, user_id = await _register_and_login(client, "reprocess@example.com")
    doc_id = await _insert_document(user_id, status="failed")

    # Stub the Celery dispatch so no real ingestion pipeline runs in tests.
    calls: list[tuple] = []
    from app.api.v1.endpoints import documents as documents_ep
    monkeypatch.setattr(
        documents_ep.process_document_task, "delay", lambda *a, **k: calls.append((a, k))
    )

    resp = await client.post(
        f"/documents/{doc_id}/reprocess",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending"
    assert not body.get("error_message")
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_reprocess_rejects_in_progress(client: AsyncClient, monkeypatch) -> None:
    """A document already processing cannot be re-dispatched."""
    token, user_id = await _register_and_login(client, "reprocess-busy@example.com")
    doc_id = await _insert_document(user_id, status="processing")

    from app.api.v1.endpoints import documents as documents_ep
    monkeypatch.setattr(documents_ep.process_document_task, "delay", lambda *a, **k: None)

    resp = await client.post(
        f"/documents/{doc_id}/reprocess",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "already_processing"


@pytest.mark.asyncio
async def test_reprocess_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(f"/documents/{uuid.uuid4()}/reprocess")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_reprocess_missing_document(client: AsyncClient) -> None:
    token, _ = await _register_and_login(client, "reprocess-404@example.com")
    resp = await client.post(
        f"/documents/{uuid.uuid4()}/reprocess",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404

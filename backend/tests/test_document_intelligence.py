"""Integration tests for the document-intelligence surface:
GET /documents/{id}/insights, /related, and /analytics/health.

LLM and embeddings are mocked so the tests are deterministic and need no
network, GPU, or API key. Ingestion runs inline (Celery eager in tests).
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class _EmbeddingDatum:
    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding


class _EmbeddingResponse:
    def __init__(self, embeddings: list[list[float]]) -> None:
        self.data = [_EmbeddingDatum(e) for e in embeddings]


def _chat_result(content: str) -> ChatResult:
    return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])


async def _auth_headers(client: AsyncClient, email: str) -> dict:
    await client.post("/auth/register", json={"email": email, "password": "securepassword123"})
    login = await client.post("/auth/login", json={"email": email, "password": "securepassword123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _upload(client: AsyncClient, headers: dict, name: str, body: bytes) -> str:
    resp = await client.post("/documents/upload", files={"file": (name, body, "text/plain")}, headers=headers)
    assert resp.status_code == 202, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
@patch("langchain_openai.chat_models.base.ChatOpenAI._agenerate", new_callable=AsyncMock)
@patch("openai.resources.embeddings.AsyncEmbeddings.create", new_callable=AsyncMock)
async def test_insights_related_and_health(mock_embed: AsyncMock, mock_chat: AsyncMock, client: AsyncClient) -> None:
    mock_embed.return_value = _EmbeddingResponse([[0.1] * 1536])
    mock_chat.return_value = _chat_result(
        "Summary: This document explains RAM and ROM and how they differ.\n"
        "Topics: RAM, ROM, computer memory\n"
        "Entities: RAM, ROM\n"
    )

    headers = await _auth_headers(client, "intel@example.com")

    # Two documents so "related" has something real to return.
    doc_a = await _upload(client, headers, "memory_notes.txt", b"RAM and ROM are types of computer memory.")
    doc_b = await _upload(client, headers, "hardware_notes.txt", b"ROM is non-volatile memory used at boot.")

    # --- Insights ---------------------------------------------------------- #
    ins = await client.get(f"/documents/{doc_a}/insights", headers=headers)
    assert ins.status_code == 200
    body = ins.json()
    assert body["available"] is True
    assert "RAM and ROM" in body["summary"]
    assert body["topics"] == ["RAM", "ROM", "computer memory"]
    assert body["entities"] == ["RAM", "ROM"]

    # Second call must be served from the cache (no extra LLM invocation).
    calls_after_first = mock_chat.await_count
    ins2 = await client.get(f"/documents/{doc_a}/insights", headers=headers)
    assert ins2.status_code == 200
    assert ins2.json()["summary"] == body["summary"]
    assert mock_chat.await_count == calls_after_first  # cached, not regenerated

    # --- Related ----------------------------------------------------------- #
    rel = await client.get(f"/documents/{doc_a}/related", headers=headers)
    assert rel.status_code == 200
    items = rel.json()["items"]
    assert any(r["document_id"] == doc_b for r in items)
    assert all(r["document_id"] != doc_a for r in items)  # never relates to itself
    assert all(0.0 <= r["similarity"] <= 1.0001 for r in items)

    # --- Workspace health -------------------------------------------------- #
    health = await client.get("/analytics/health", headers=headers)
    assert health.status_code == 200
    h = health.json()
    assert h["total_documents"] == 2
    assert h["indexed_documents"] == 2
    assert h["processing_documents"] == 0
    assert h["failed_documents"] == 0
    assert h["knowledge_base_health"] == "healthy"
    assert len(h["recent_activity"]) == 2


@pytest.mark.asyncio
async def test_insights_unavailable_before_indexing(client: AsyncClient) -> None:
    """Insights on a not-yet-completed document report available=false, never fabricate."""
    import uuid
    from app.models.document import Document
    import app.db.session as db_session

    headers = await _auth_headers(client, "pending@example.com")

    # Create a document row stuck in 'processing' (no chunks, not indexed).
    me = await client.get("/auth/me", headers=headers)
    user_id = uuid.UUID(me.json()["id"])
    async with db_session.AsyncSessionLocal() as session:
        doc = Document(
            user_id=user_id, filename="pending.txt", file_type=".txt",
            storage_path="x/pending.txt", file_size=10, status="processing",
        )
        session.add(doc)
        await session.commit()
        doc_id = str(doc.id)

    resp = await client.get(f"/documents/{doc_id}/insights", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert body["summary"] is None
    assert body["topics"] == [] and body["entities"] == []


@pytest.mark.asyncio
async def test_intelligence_endpoints_require_ownership(client: AsyncClient) -> None:
    """A user cannot read another user's document intelligence (404, no leak)."""
    import uuid
    headers = await _auth_headers(client, "owner2@example.com")
    ghost = uuid.uuid4()
    for path in (f"/documents/{ghost}/insights", f"/documents/{ghost}/related"):
        resp = await client.get(path, headers=headers)
        assert resp.status_code == 404

from __future__ import annotations

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch
import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.chat import ChatMessage, ChatSession
from app.models.document import Document, DocumentChunk
from app.models.usage import UsageLog
from app.services.rag.citations import CitationEngine
from app.services.rag.embeddings import LocalEmbeddingProvider, OpenAIEmbeddingProvider
from app.services.rag.evaluator import RAGEvaluator
from app.services.rag.retriever import HybridRetriever, reciprocal_rank_fusion
from app.services.rag.vector_db import QdrantService


# --------------------------------------------------------------------------- #
# Mocks & Stubs
# --------------------------------------------------------------------------- #
class MockEmbeddingData:
    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding


class MockEmbeddingResponse:
    def __init__(self, embeddings: list[list[float]]) -> None:
        self.data = [MockEmbeddingData(emb) for emb in embeddings]


class MockMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class MockChoice:
    def __init__(self, content: str) -> None:
        self.message = MockMessage(content)


class MockCompletionResponse:
    def __init__(self, content: str) -> None:
        self.choices = [MockChoice(content)]


# Stream chunk mock structures
class MockDelta:
    def __init__(self, content: str | None) -> None:
        self.content = content


class MockStreamChoice:
    def __init__(self, content: str | None) -> None:
        self.delta = MockDelta(content)


class MockStreamChunk:
    def __init__(self, content: str | None) -> None:
        self.choices = [MockStreamChoice(content)]


async def async_stream_generator(tokens: list[str]) -> AsyncGenerator[Any, None]:
    for token in tokens:
        yield MockStreamChunk(token)


# --------------------------------------------------------------------------- #
# Embedding Provider Tests
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_openai_embedding_provider_batching() -> None:
    """Test batching and exception handling in OpenAIEmbeddingProvider."""
    with patch("openai.resources.embeddings.AsyncEmbeddings.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = MockEmbeddingResponse([[0.1] * 1536, [0.2] * 1536])
        
        provider = OpenAIEmbeddingProvider()
        embeddings = await provider.embed_documents(["hello", "world"])
        
        assert len(embeddings) == 2
        assert embeddings[0][0] == 0.1
        assert embeddings[1][0] == 0.2
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_local_embedding_provider() -> None:
    """Verify local SentenceTransformer embeddings dimension."""
    provider = LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2")
    # MiniLM dimensions is 384
    query_vector = await provider.embed_query("Search text query")
    assert len(query_vector) == 384
    
    docs_vectors = await provider.embed_documents(["doc 1 content", "doc 2 content"])
    assert len(docs_vectors) == 2
    assert len(docs_vectors[0]) == 384


# --------------------------------------------------------------------------- #
# Vector Database & Multi-Tenant Isolation Tests
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_qdrant_multi_tenant_isolation() -> None:
    """Test Qdrant CRUD and verify user B cannot query user A's document points."""
    qdrant = QdrantService()
    collection_name = "test_chunks"
    
    # 1. Provision collection
    await qdrant.create_collection_if_not_exists(collection_name, 4)

    # 2. Setup mock chunks
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    chunk_1 = DocumentChunk(id=uuid.uuid4(), document_id=doc_id, chunk_index=0, content="Private financial report A", page_number=1)
    chunk_2 = DocumentChunk(id=uuid.uuid4(), document_id=doc_id, chunk_index=1, content="General manual B", page_number=2)

    # 3. Upsert
    await qdrant.upsert_chunks(
        collection_name,
        [chunk_1, chunk_2],
        [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]],
        user_a_id,
    )

    # 4. Search as User A -> Should return both chunks
    results_a = await qdrant.search_chunks(
        collection_name, [0.1, 0.2, 0.3, 0.4], user_a_id, limit=5
    )
    assert len(results_a) == 2
    assert any("report A" in r["payload"]["content"] for r in results_a)

    # 5. Search as User B -> Should return NOTHING (Strict multi-tenancy)
    results_b = await qdrant.search_chunks(
        collection_name, [0.1, 0.2, 0.3, 0.4], user_b_id, limit=5
    )
    assert len(results_b) == 0

    # 6. Delete document points
    await qdrant.delete_by_document(collection_name, doc_id, user_a_id)
    results_after_delete = await qdrant.search_chunks(
        collection_name, [0.1, 0.2, 0.3, 0.4], user_a_id, limit=5
    )
    assert len(results_after_delete) == 0


# --------------------------------------------------------------------------- #
# RRF & Sparse BM25 Search Tests
# --------------------------------------------------------------------------- #
def test_rrf_scoring_math() -> None:
    """Verify RRF correctly merges ranked outputs of dense and sparse lookups."""
    # Chunk 1: Rank 1 in dense, Rank 2 in sparse
    # Chunk 2: Rank 2 in dense, Rank 1 in sparse
    # Chunk 3: Rank 3 in dense, absent in sparse
    dense = [
        {"chunk_id": uuid.UUID("11111111-1111-1111-1111-111111111111"), "score": 0.9, "payload": {"content": "text 1"}},
        {"chunk_id": uuid.UUID("22222222-2222-2222-2222-222222222222"), "score": 0.8, "payload": {"content": "text 2"}},
        {"chunk_id": uuid.UUID("33333333-3333-3333-3333-333333333333"), "score": 0.7, "payload": {"content": "text 3"}},
    ]
    sparse = [
        {"chunk_id": uuid.UUID("22222222-2222-2222-2222-222222222222"), "score": 12.5, "payload": {"content": "text 2"}},
        {"chunk_id": uuid.UUID("11111111-1111-1111-1111-111111111111"), "score": 9.2, "payload": {"content": "text 1"}},
    ]

    fused = reciprocal_rank_fusion(dense, sparse, k=60)
    
    # RRF score chunk 1: 1/(60+1) + 1/(60+2) = 0.01639 + 0.01612 = 0.03251
    # RRF score chunk 2: 1/(60+2) + 1/(60+1) = 0.03251
    # RRF score chunk 3: 1/(60+3) = 0.01587
    assert len(fused) == 3
    assert fused[0]["chunk_id"] in (dense[0]["chunk_id"], dense[1]["chunk_id"])
    assert fused[2]["chunk_id"] == dense[2]["chunk_id"]
    assert fused[2]["score"] == pytest.approx(1 / 63)


# --------------------------------------------------------------------------- #
# Citation Engine Tests
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@patch("openai.resources.embeddings.AsyncEmbeddings.create", new_callable=AsyncMock)
async def test_citation_parsing_and_excerpt_mapping(
    mock_embed: AsyncMock,
    client: AsyncClient,
) -> None:
    """Verify that citations match index positions and retrieve correct filenames from DB."""
    # Create user & document to resolve name lookups
    await client.post(
        "/auth/register",
        json={"email": "citationuser@example.com", "password": "securepassword123"},
    )
    login_resp = await client.post(
        "/auth/login",
        json={"email": "citationuser@example.com", "password": "securepassword123"},
    )
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # Upload mock document to create db record
    mock_embed.return_value = MockEmbeddingResponse([[0.1] * 1536])
    files = {"file": ("manual_handbook.txt", b"Grounded information content", "text/plain")}
    upload_resp = await client.post("/documents/upload", files=files, headers=headers)
    doc_id = upload_resp.json()["id"]

    retrieved = [
        {
            "chunk_id": uuid.uuid4(),
            "score": 0.85,
            "payload": {
                "document_id": doc_id,
                "chunk_index": 0,
                "page_number": 1,
                "content": "Grounded information content",
            }
        }
    ]

    engine = CitationEngine()
    response_text = "This matches the handbook manual details [1]."
    
    text, citations = await engine.extract_citations(response_text, retrieved)

    assert len(citations) == 1
    assert citations[0]["document_name"] == "manual_handbook.txt"
    assert citations[0]["page_number"] == 1
    assert citations[0]["supporting_excerpt"] == "Grounded information content"
    assert citations[0]["confidence_score"] == 0.85


# --------------------------------------------------------------------------- #
# End-to-End Chat API & Streaming Integration Tests
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@patch("openai.resources.chat.completions.AsyncCompletions.create", new_callable=AsyncMock)
@patch("openai.resources.embeddings.AsyncEmbeddings.create", new_callable=AsyncMock)
async def test_streaming_chat_e2e_completions(
    mock_embed: AsyncMock,
    mock_chat: AsyncMock,
    client: AsyncClient,
) -> None:
    """Test end-to-end chat creation, RAG streaming, telemetry log writing, and deletion."""
    # 1. Auth registers and logins
    await client.post(
        "/auth/register",
        json={"email": "chatuser@example.com", "password": "securepassword123"},
    )
    login_resp = await client.post(
        "/auth/login",
        json={"email": "chatuser@example.com", "password": "securepassword123"},
    )
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Upload Document & trigger eager worker pipeline (inserts vectors and chunks)
    mock_embed.return_value = MockEmbeddingResponse([[0.1] * 1536])
    files = {"file": ("manual_ingestion.txt", b"RAG citation context manual information.", "text/plain")}
    upload_resp = await client.post("/documents/upload", files=files, headers=headers)
    doc_id = upload_resp.json()["id"]

    # 3. Create Chat Session
    session_resp = await client.post(
        "/chat/sessions",
        json={"title": "RAG Testing Conversation"},
        headers=headers,
    )
    assert session_resp.status_code == 201
    session_data = session_resp.json()
    session_id = session_data["id"]

    # 4. Stream Message Response
    # Mock LLM generation stream
    tokens = ["This", " is", " verified", " content", " matching", " manual", " [1]."]
    mock_chat.return_value = async_stream_generator(tokens)

    message_payload = {
        "content": "Verify contextual information",
        "document_ids": [doc_id],
        "multi_query": False,
        "expand_context": False,
    }

    # Send message completion request
    response = await client.post(
        f"/chat/sessions/{session_id}/messages",
        json=message_payload,
        headers=headers,
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # Parse SSE stream contents
    raw_lines = response.text.split("\n\n")
    stream_content = []
    citations = []

    for line in raw_lines:
        if line.startswith("data: "):
            payload_str = line.replace("data: ", "")
            if payload_str.strip() == "[DONE]":
                continue
            payload = json.loads(payload_str)
            if payload["type"] == "content":
                stream_content.append(payload["content"])
            elif payload["type"] == "citations":
                citations = payload["citations"]

    full_answer = "".join(stream_content)
    assert "verified content" in full_answer
    assert len(citations) == 1
    assert citations[0]["document_name"] == "manual_ingestion.txt"

    # Verify message persistence in DB
    async with AsyncSessionLocal() as db:
        # User message and assistant message should both be stored (2 messages total)
        stmt = select(ChatMessage).where(ChatMessage.chat_id == uuid.UUID(session_id))
        res = await db.execute(stmt)
        messages = res.scalars().all()
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert messages[1].citations is not None
        assert len(messages[1].citations) == 1

        # Check telemetry logs
        log_stmt = select(UsageLog).where(UsageLog.action == "chat_completion")
        log_res = await db.execute(log_stmt)
        logs = log_res.scalars().all()
        assert len(logs) == 1
        assert logs[0].extra_info["citations_found"] == 1

    # 5. Fetch Chat Session Detail (should preload messages)
    detail_resp = await client.get(f"/chat/sessions/{session_id}", headers=headers)
    assert detail_resp.status_code == 200
    assert len(detail_resp.json()["messages"]) == 2

    # 6. Fetch Analytics Summary
    analytics_resp = await client.get("/analytics/summary", headers=headers)
    assert analytics_resp.status_code == 200
    analytics_data = analytics_resp.json()
    assert analytics_data["total_requests"] >= 1
    assert "chat_completion" in analytics_data["latencies_breakdown"]

    # 7. Delete Session
    del_resp = await client.delete(f"/chat/sessions/{session_id}", headers=headers)
    assert del_resp.status_code == 204

    # Clean up local mock vector databases
    qdrant = QdrantService()
    if qdrant.client:
        qdrant.client.close()

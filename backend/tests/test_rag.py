from __future__ import annotations

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch
import uuid

from httpx import AsyncClient
from sqlalchemy import select

from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from app.db.session import AsyncSessionLocal
from app.models.chat import ChatMessage, ChatSession
from app.models.document import Document, DocumentChunk
from app.models.usage import UsageLog
from app.services.rag.chat import ChatService
from app.services.rag.citations import CitationEngine
from app.services.rag.embeddings import LocalEmbeddingProvider, OpenAIEmbeddingProvider
from app.services.rag.evaluator import RAGEvaluator
from app.services.rag.retriever import HybridRetriever, reciprocal_rank_fusion
from app.services.rag.vector_store import QdrantAdapter


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
    pytest.importorskip("sentence_transformers")
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
    qdrant = QdrantAdapter()
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
@patch("app.services.rag.reranker.CrossEncoderReranker.rerank", new_callable=AsyncMock)
@patch("langchain_openai.chat_models.base.ChatOpenAI._agenerate", new_callable=AsyncMock)
@patch("openai.resources.embeddings.AsyncEmbeddings.create", new_callable=AsyncMock)
async def test_streaming_chat_e2e_completions(
    mock_embed: AsyncMock,
    mock_chat: AsyncMock,
    mock_rerank: AsyncMock,
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
    # Mock reranker to pass candidates through unchanged (sentence_transformers optional dep)
    mock_rerank.side_effect = lambda query, candidates: candidates

    # Mock LLM non-streaming calls (planner node)
    def _make_chat_result(content: str) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    mock_chat.side_effect = [
        _make_chat_result("Plan: retrieve and synthesize information."),
        _make_chat_result("This is verified content matching manual [1]."),
    ]

    # Mock LLM streaming call (reasoner node uses llm.astream)
    # _astream is an async generator; AsyncMock can't replicate it, so patch class-level.
    from langchain_openai.chat_models.base import ChatOpenAI as _ChatOpenAI
    _original_astream = _ChatOpenAI._astream

    async def _mock_astream(self, *args, **kwargs):
            text = "This is verified content matching manual [1]."
            for token in text.split(" "):
                yield ChatGenerationChunk(message=AIMessageChunk(content=token + " "))

    _ChatOpenAI._astream = _mock_astream

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
        log_stmt = select(UsageLog).where(UsageLog.action == "agent_completion")
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
    assert "agent_completion" in analytics_data["latencies_breakdown"]

    # 6.5. Update (Rename / Pin) Session
    patch_resp = await client.patch(
        f"/chat/sessions/{session_id}",
        json={"title": "Renamed Testing Chat", "is_pinned": True},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Renamed Testing Chat"
    assert patch_resp.json()["is_pinned"] is True

    # 6.6. Verify rename persisted
    get_resp = await client.get(f"/chat/sessions/{session_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Renamed Testing Chat"
    assert get_resp.json()["is_pinned"] is True

    # 7. Delete Session
    del_resp = await client.delete(f"/chat/sessions/{session_id}", headers=headers)
    assert del_resp.status_code == 204

    # Clean up local mock vector databases
    qdrant = QdrantAdapter()
    if qdrant.client:
        await qdrant.client.close()

    # Restore original async generator
    _ChatOpenAI._astream = _original_astream


# --------------------------------------------------------------------------- #
# Cache-Hit Persistence Regression Tests
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@patch("app.services.rag.chat.ChatService._check_cache", new_callable=AsyncMock)
async def test_cache_hit_persists_user_and_assistant_messages(
    mock_check_cache: AsyncMock,
    client: AsyncClient,
) -> None:
    """Regression: cache-hit path must persist both user and assistant messages
    so the conversation survives a page reload.  This was the core bug where
    stream_chat_response returned early without any DB writes on a cache hit."""

    # Force every _check_cache call to return a pre-built cached payload.
    cached_payload: dict = {
        "final_response": "Caching stores frequently accessed data for speed.",
        "citations": [
            {
                "document_name": "cache_guide.pdf",
                "document_id": None,
                "page_number": 2,
                "supporting_excerpt": "Frequently accessed data",
                "confidence_score": 0.91,
            }
        ],
        "confidence": 0.91,
        "chunk_count": 3,
        "token_count": 22,
    }
    mock_check_cache.return_value = cached_payload

    # Auth
    await client.post(
        "/auth/register",
        json={"email": "cachetest@example.com", "password": "pass123456"},
    )
    login = await client.post(
        "/auth/login",
        json={"email": "cachetest@example.com", "password": "pass123456"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Create a fresh session
    sess = await client.post(
        "/chat/sessions",
        json={"title": "Cache Persistence Test"},
        headers=headers,
    )
    assert sess.status_code == 201
    session_id = sess.json()["id"]

    # Send the message — _check_cache is mocked → cache-hit path is executed
    response = await client.post(
        f"/chat/sessions/{session_id}/messages",
        json={"content": "What is caching?"},
        headers=headers,
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # Parse SSE stream and verify all expected events are present
    content_parts: list[str] = []
    received_citations: list[dict] = []
    received_stats: dict = {}
    seen_done = False

    for chunk in response.text.split("\n\n"):
        chunk = chunk.strip()
        if not chunk.startswith("data: "):
            continue
        raw = chunk[6:].strip()
        if raw == "[DONE]":
            seen_done = True
            continue
        event = json.loads(raw)
        if event["type"] == "content":
            content_parts.append(event["content"])
        elif event["type"] == "citations":
            received_citations = event["citations"]
        elif event["type"] == "stats":
            received_stats = event

    assert seen_done, "Stream did not terminate with [DONE]"
    full_text = "".join(content_parts)
    assert "Caching stores" in full_text
    assert len(received_citations) == 1
    assert received_citations[0]["document_name"] == "cache_guide.pdf"
    assert received_stats.get("cached") is True
    assert received_stats.get("confidence") == pytest.approx(0.91)
    assert received_stats.get("chunk_count") == 3

    # Both messages must now be in the database
    async with AsyncSessionLocal() as db:
        stmt = select(ChatMessage).where(ChatMessage.chat_id == uuid.UUID(session_id))
        result = await db.execute(stmt)
        msgs = list(result.scalars().all())

    assert len(msgs) == 2, (
        f"Expected 2 persisted messages (user + assistant) after cache hit, got {len(msgs)}"
    )

    user_msg = next(m for m in msgs if m.role == "user")
    asst_msg = next(m for m in msgs if m.role == "assistant")

    # User message
    assert user_msg.content == "What is caching?"

    # Assistant message content
    assert "Caching stores" in asst_msg.content

    # Citations must be persisted
    assert asst_msg.citations is not None
    assert len(asst_msg.citations) == 1
    assert asst_msg.citations[0]["document_name"] == "cache_guide.pdf"

    # Metadata must be fully persisted
    meta = asst_msg.meta
    assert meta is not None
    assert meta.get("cached") is True
    assert meta.get("confidence") == pytest.approx(0.91)
    assert meta.get("chunkCount") == 3
    assert meta.get("tokenCount") is not None
    assert meta.get("totalMs") is not None
    assert meta.get("latencyMs") is not None
    assert meta.get("model") is not None
    assert meta.get("provider") is not None

    # Simulated reload: session detail must return both messages
    detail = await client.get(f"/chat/sessions/{session_id}", headers=headers)
    assert detail.status_code == 200
    detail_msgs = detail.json()["messages"]
    assert len(detail_msgs) == 2, (
        f"Session detail returned {len(detail_msgs)} messages after cache hit; expected 2"
    )
    assert detail_msgs[0]["role"] == "user"
    assert detail_msgs[1]["role"] == "assistant"
    # Metadata intact on reload
    assert detail_msgs[1]["meta"]["cached"] is True
    assert detail_msgs[1]["meta"]["chunkCount"] == 3
    # Citations intact on reload
    assert detail_msgs[1]["citations"] is not None
    assert len(detail_msgs[1]["citations"]) == 1
    assert detail_msgs[1]["citations"][0]["document_name"] == "cache_guide.pdf"


@pytest.mark.asyncio
@patch("app.services.rag.chat.ChatService._check_cache", new_callable=AsyncMock)
async def test_cache_hit_derives_session_title(
    mock_check_cache: AsyncMock,
    client: AsyncClient,
) -> None:
    """Title derivation must run even when the answer comes from cache."""
    mock_check_cache.return_value = {
        "final_response": "Answer from cache.",
        "citations": [],
        "confidence": 0.8,
        "chunk_count": 0,
        "token_count": 10,
    }

    await client.post(
        "/auth/register",
        json={"email": "titlecache@example.com", "password": "pass123456"},
    )
    login = await client.post(
        "/auth/login",
        json={"email": "titlecache@example.com", "password": "pass123456"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Session starts with the default "New Chat" placeholder title
    sess = await client.post("/chat/sessions", json={"title": "New Chat"}, headers=headers)
    session_id = sess.json()["id"]

    await client.post(
        f"/chat/sessions/{session_id}/messages",
        json={"content": "Tell me about machine learning"},
        headers=headers,
    )

    # Title should now be derived from the first user message
    detail = await client.get(f"/chat/sessions/{session_id}", headers=headers)
    title = detail.json()["title"]
    assert title.lower() != "new chat", f"Title was not updated from default; got: {title!r}"
    assert "machine learning" in title.lower() or "Machine Learning" in title

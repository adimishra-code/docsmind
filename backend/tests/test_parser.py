from __future__ import annotations

import io
import pytest
import shutil
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from app.services.parser.chunker import get_chunker
from app.services.parser.cleaner import sanitize_text
from app.services.parser.parsers import CsvParser, TxtParser
from app.services.storage.local import LocalStorage


# --------------------------------------------------------------------------- #
# Unit Tests
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_local_storage_lifecycle() -> None:
    """Test LocalStorage write, retrieve, and delete capabilities."""
    storage = LocalStorage(base_dir="test_storage")
    test_data = b"Testing storage system integrity"
    storage_key = "user_1/test_doc.txt"

    try:
        # 1. Upload
        stored_path = await storage.upload(test_data, storage_key)
        assert "test_doc.txt" in stored_path

        # 2. Download
        retrieved_data = await storage.download(stored_path)
        assert retrieved_data == test_data

        # 3. Delete
        await storage.delete(stored_path)
        
        # Verify deletion causes a NotFoundError
        with pytest.raises(Exception):
            await storage.download(stored_path)
            
    finally:
        # Clean up test directory
        if storage.base_path.exists():
            shutil.rmtree(storage.base_path)


def test_txt_parser() -> None:
    """Test plain text parser extraction."""
    parser = TxtParser()
    content = b"# Heading 1\nThis is paragraph 1.\n## Heading 2\nParagraph 2."
    text, meta = parser.parse(content)

    assert "Heading 1" in text
    assert "Paragraph 2" in text
    assert len(meta["headings"]) == 2
    assert meta["headings"][0]["text"] == "Heading 1"
    assert meta["headings"][1]["level"] == 2


def test_csv_parser() -> None:
    """Test CSV formatting as GFM Markdown tables."""
    parser = CsvParser()
    content = b"Name,Age,Role\nAlice,30,Engineer\nBob,25,Designer"
    text, meta = parser.parse(content)

    assert "| Name | Age | Role |" in text
    assert "| Alice | 30 | Engineer |" in text
    assert meta["rows_count"] == 3
    assert meta["cols_count"] == 3


def test_text_cleaner() -> None:
    """Test character normalization and spacing cleanup."""
    raw = "This   is   a    spaced  sentence.\n\n\n\nNew paragraph with 'smart' curly quotes: “Hello”."
    clean = sanitize_text(raw)
    
    assert "This is a spaced sentence." in clean
    assert '\n\nNew paragraph with \'smart\' curly quotes: "Hello".' in clean


def test_recursive_character_chunker() -> None:
    """Test recursive character text splitting constraints."""
    text = "Word " * 200  # 1000 characters
    chunker = get_chunker("recursive_character", chunk_size=500, chunk_overlap=100)
    chunks = chunker.split_text(text)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk["content"]) <= 500
        assert chunk["metadata"]["strategy"] == "recursive_character"


def test_token_based_chunker() -> None:
    """Test token-based text splitting constraints using tiktoken."""
    text = "Word " * 300
    chunker = get_chunker("token_based", chunk_size=100, chunk_overlap=20)
    chunks = chunker.split_text(text)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk["metadata"]["token_count"] <= 100
        assert chunk["metadata"]["strategy"] == "token_based"


# --------------------------------------------------------------------------- #
# Integration E2E Tests
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@patch("app.services.rag.embeddings.OpenAIEmbeddingProvider.embed_documents", new_callable=AsyncMock)
async def test_document_ingestion_e2e_lifecycle(
    mock_embed: AsyncMock,
    client: AsyncClient,
) -> None:
    """Test complete document upload, processing, status querying, and deletion."""
    # 1. Register and Login to get access token
    await client.post(
        "/auth/register",
        json={"email": "parseruser@example.com", "password": "securepassword123"},
    )
    login_resp = await client.post(
        "/auth/login",
        json={"email": "parseruser@example.com", "password": "securepassword123"},
    )
    access_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Upload Document
    mock_embed.return_value = [[0.1] * 1536]
    file_name = "test_ingestion.txt"
    file_content = b"# Platform Manual\nThis is paragraph content describing RAG pipelines."
    files = {"file": (file_name, io.BytesIO(file_content), "text/plain")}
    
    upload_resp = await client.post(
        "/documents/upload",
        files=files,
        data={"chunk_size": 256, "chunk_overlap": 32},
        headers=headers,
    )
    
    assert upload_resp.status_code == 202
    doc_data = upload_resp.json()
    doc_id = doc_data["id"]
    assert doc_data["filename"] == file_name
    assert doc_data["status"] == "pending"  # HTTP response is pending immediately on upload

    # 3. Retrieve Status details
    status_resp = await client.get(f"/documents/{doc_id}/status", headers=headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "completed"
    assert status_data["progress_pct"] == 100.0

    # 4. Fetch Document details
    detail_resp = await client.get(f"/documents/{doc_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["doc_metadata"]["document_type"] == "txt"
    assert detail_data["doc_metadata"]["language"] == "en"
    assert "Platform Manual" in detail_data["doc_metadata"]["title"]

    # 5. List Documents
    list_resp = await client.get("/documents", headers=headers)
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["id"] == doc_id

    # 6. Delete Document
    del_resp = await client.delete(f"/documents/{doc_id}", headers=headers)
    assert del_resp.status_code == 204

    # Verify document is no longer queryable
    check_deleted_resp = await client.get(f"/documents/{doc_id}", headers=headers)
    assert check_deleted_resp.status_code == 404

"""Regression test for single-query retrieval relevance.

The bug: for a focused question ("projects of Aditya Mishra"), cross-document
diversity injected unrelated-document chunks (EPROM/PROM/Mughal) into the final
context and evicted the relevant document's lower-ranked chunks. The single-query
path must now return pure top-K by relevance and never inject unrelated docs.
"""
from __future__ import annotations

import uuid

import pytest

from app.services.rag.retriever import HybridRetriever


@pytest.mark.asyncio
async def test_single_query_returns_pure_relevance_no_unrelated_injection() -> None:
    r = HybridRetriever()

    # The relevant document ("cv") supplies 8 highly-relevant chunks; an
    # unrelated document supplies lower-scored chunks.
    cv = [
        {"chunk_id": f"cv{i}", "score": 1.0 - i * 0.01,
         "payload": {"document_id": "cv", "chunk_index": i, "page_number": 1, "content": f"cv chunk {i}"}}
        for i in range(8)
    ]
    unrelated = [
        {"chunk_id": f"x{i}", "score": 0.4,
         "payload": {"document_id": "other", "chunk_index": i, "page_number": 1, "content": f"EPROM PROM {i}"}}
        for i in range(4)
    ]

    async def fake_embed_query(_q: str):
        return [0.1] * 8

    async def fake_create(*_a, **_k):
        return None

    async def fake_dense(_q, _u, limit, _d):
        return cv[:limit]

    async def fake_sparse(_q, _u, *, limit=10, document_ids=None):
        return unrelated[:limit]

    async def fake_rerank(_q, candidates):
        # Model a working cross-encoder: the CV/project content is relevant to the
        # query; the unrelated "EPROM/PROM" content is not. (RRF has by now
        # overwritten the raw `score` with rank-based values, so relevance must
        # come from the reranker — exactly as in production.)
        out = []
        for c in candidates:
            c = dict(c)
            c["rerank_score"] = 1.0 if (c.get("payload") or {}).get("document_id") == "cv" else 0.05
            out.append(c)
        out.sort(key=lambda x: x["rerank_score"], reverse=True)
        return out

    r.embedding_provider.embed_query = fake_embed_query
    r.vector_store.create_collection_if_not_exists = fake_create
    r._retrieve_dense = fake_dense
    r.sparse_searcher.search = fake_sparse
    r.reranker.rerank = fake_rerank

    result = await r.retrieve("projects of aditya mishra", uuid.uuid4(), limit=8)

    docs = {c["payload"]["document_id"] for c in result}
    # Only the relevant document's chunks — no unrelated-document injection.
    assert docs == {"cv"}, f"unrelated documents were injected: {docs}"
    assert len(result) == 8

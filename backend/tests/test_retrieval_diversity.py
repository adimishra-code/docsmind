"""Unit tests for cross-document diversity in the hybrid retriever.

The regression this guards: a single strongly-matching document filling every
final slot, which starved other relevant documents and made multi-document
questions fail with a false "not found".
"""
from __future__ import annotations

from app.services.rag.retriever import HybridRetriever


def _cand(doc: str, idx: int, score: float = 1.0) -> dict:
    return {"chunk_id": f"{doc}-{idx}", "score": score, "payload": {"document_id": doc, "chunk_index": idx}}


def test_diversify_spreads_across_documents() -> None:
    # Reranker returned 6 chunks from doc A then 3 from docs B and C — the old
    # top-5 slice would have been all-A.
    ranked = (
        [_cand("A", i) for i in range(6)]
        + [_cand("B", i) for i in range(2)]
        + [_cand("C", i) for i in range(2)]
    )
    out = HybridRetriever._diversify_by_document(ranked, limit=6)

    docs = {c["payload"]["document_id"] for c in out}
    assert docs == {"A", "B", "C"}, "every relevant document must be represented"
    # The dominant document keeps its guaranteed relevant half (3 of 6), but the
    # other documents still appear — breadth without starving relevance.
    assert sum(1 for c in out if c["payload"]["document_id"] == "A") == 3
    assert sum(1 for c in out if c["payload"]["document_id"] == "B") >= 1
    assert sum(1 for c in out if c["payload"]["document_id"] == "C") >= 1


def test_diversify_keeps_dominant_documents_relevant_section() -> None:
    # Regression for the "projects in Aditya's CV not found" bug: the CV is the
    # most relevant document and its 4th-ranked chunk is the Projects section;
    # other documents only weakly match. The old hard per-document cap (3 for
    # limit 8) dropped the Projects chunk entirely. The relevance-guaranteed pass
    # must keep it, while still giving the other documents representation.
    ranked = (
        [_cand("cv", i, 1.0 - i * 0.01) for i in range(5)]      # cv-3 == Projects
        + [_cand("other", i, 0.5 - i * 0.01) for i in range(4)]
    )
    out = HybridRetriever._diversify_by_document(ranked, limit=8)
    ids = {c["chunk_id"] for c in out}
    assert "cv-3" in ids, "the dominant document's Projects section must survive diversity"
    assert any(c["payload"]["document_id"] == "other" for c in out), "breadth preserved"


def test_diversify_preserves_single_document_questions() -> None:
    # Only one document is relevant — diversity must not drop results or reorder.
    ranked = [_cand("A", i) for i in range(5)]
    out = HybridRetriever._diversify_by_document(ranked, limit=8)
    assert [c["chunk_id"] for c in out] == [c["chunk_id"] for c in ranked]


def test_diversify_backfills_to_limit() -> None:
    # Two docs, limit larger than max_per_doc*docs would allow in pass one:
    # remaining slots backfill by relevance so we still return `limit` items.
    ranked = [_cand("A", i) for i in range(10)] + [_cand("B", i) for i in range(2)]
    out = HybridRetriever._diversify_by_document(ranked, limit=8)
    assert len(out) == 8
    assert {c["payload"]["document_id"] for c in out} == {"A", "B"}

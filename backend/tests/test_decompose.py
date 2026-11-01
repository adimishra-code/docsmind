"""Unit tests for multi-part question decomposition and context merging."""
from __future__ import annotations

from app.services.agents.decompose import looks_multipart, parse_subquestions
from app.services.rag.retriever import HybridRetriever


def test_single_question_is_not_multipart() -> None:
    assert not looks_multipart("What is the difference between RAM and ROM?")
    assert not looks_multipart("Summarize the Gandhara school of art")
    assert not looks_multipart("Explain photosynthesis")


def test_multipart_detected_by_separators() -> None:
    assert looks_multipart(
        "Difference between RAM and ROM, types of RAM, projects by Aditya Mishra"
    )
    assert looks_multipart("Explain RAM\nExplain ROM\nSummarize Gandhara vs Mathura")


def test_multipart_detected_by_multiple_questions() -> None:
    assert looks_multipart("What is RAM? What is ROM?")


def test_parse_subquestions_cleans_and_dedupes() -> None:
    raw = "1. Types of RAM\n- Types of ROM\nTypes of RAM\n\n  Projects by Aditya  "
    tasks = parse_subquestions(raw, "original prompt")
    assert tasks == ["Types of RAM", "Types of ROM", "Projects by Aditya"]


def test_parse_subquestions_falls_back_to_original() -> None:
    assert parse_subquestions("", "My original question") == ["My original question"]
    # Lines too short to be real questions are dropped, then fall back.
    assert parse_subquestions("a\nb\n?", "My original question") == ["My original question"]


def _cand(doc: str, idx: int, score: float) -> dict:
    return {
        "chunk_id": f"{doc}-{idx}",
        "score": score,
        "payload": {"document_id": doc, "chunk_index": idx},
    }


def test_merge_runs_dedupes_balances_and_orders() -> None:
    # Two sub-questions; one shared chunk (A-0) appears in both runs.
    run1 = [_cand("A", 0, 0.9), _cand("A", 3, 0.8), _cand("A", 1, 0.7)]
    run2 = [_cand("A", 0, 0.95), _cand("B", 5, 0.6), _cand("B", 2, 0.5)]

    merged = HybridRetriever.merge_runs([run1, run2], total_limit=6)

    ids = [c["chunk_id"] for c in merged]
    # De-duplicated: A-0 appears exactly once.
    assert ids.count("A-0") == 1
    # Both documents represented (balancing).
    assert {c["payload"]["document_id"] for c in merged} == {"A", "B"}
    # Chunks from the same document are ordered by chunk_index (logical packing).
    a_indices = [c["payload"]["chunk_index"] for c in merged if c["payload"]["document_id"] == "A"]
    assert a_indices == sorted(a_indices)

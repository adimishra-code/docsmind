"""Unit tests for document-insight parsing (label-based, model-agnostic)."""
from __future__ import annotations

from app.services.rag.insights import parse_insights


def test_parses_well_formed_output() -> None:
    raw = (
        "Summary: This document covers the Gandhara school of art and its Greco-Buddhist "
        "influences. It contrasts it with the Mathura school.\n"
        "Topics: Gandhara art, Mathura art, Buddhist sculpture\n"
        "Entities: Gandhara, Mathura, Kushan Empire\n"
    )
    out = parse_insights(raw)
    assert out["summary"].startswith("This document covers the Gandhara")
    assert out["topics"] == ["Gandhara art", "Mathura art", "Buddhist sculpture"]
    assert out["entities"] == ["Gandhara", "Mathura", "Kushan Empire"]


def test_handles_missing_sections_and_none() -> None:
    out = parse_insights("Summary: A short note about caching.\nTopics: caching\nEntities: none")
    assert out["summary"] == "A short note about caching."
    assert out["topics"] == ["caching"]
    assert out["entities"] == []  # "none" is dropped, never shown as a fake entity


def test_empty_output_yields_no_summary() -> None:
    out = parse_insights("")
    assert out["summary"] is None
    assert out["topics"] == []
    assert out["entities"] == []


def test_deduplicates_and_strips_bullets() -> None:
    out = parse_insights("Summary: x\nTopics: - RAM, RAM, ROM\nEntities: 1. Intel, Intel")
    assert out["topics"] == ["RAM", "ROM"]
    assert out["entities"] == ["Intel"]

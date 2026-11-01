"""Unit tests for conversation auto-titling from the first user message."""
from __future__ import annotations

from app.services.rag.chat import _DEFAULT_TITLES, _derive_title


def test_short_message_used_verbatim() -> None:
    assert _derive_title("Difference between RAM and ROM") == "Difference between RAM and ROM"


def test_long_message_is_trimmed_on_word_boundary() -> None:
    title = _derive_title(
        "Explain in detail the differences between Gandhara and Mathura schools of art"
    )
    assert len(title) <= 49  # 48 chars + ellipsis
    assert title.endswith("…")
    assert "  " not in title


def test_whitespace_is_collapsed() -> None:
    assert _derive_title("  Projects   by\nAditya   Mishra ") == "Projects by Aditya Mishra"


def test_empty_falls_back() -> None:
    assert _derive_title("   ") == "New Chat"


def test_strips_conversational_lead_in_to_topic_title() -> None:
    # The reported case: the title must be the TOPIC, not the raw first sentence.
    title = _derive_title("can you tell me about the projects made by aditya mishra")
    assert title == "Projects Made by Aditya Mishra"
    assert "can you" not in title.lower()


def test_preserves_acronyms_and_connectors() -> None:
    assert _derive_title("what is the difference between RAM and ROM") == "Difference between RAM and ROM"
    assert _derive_title("tell me about Gandhara vs Mathura") == "Gandhara vs Mathura"


def test_falls_back_when_only_scaffolding() -> None:
    # "tell me about" alone leaves nothing — keep the original rather than blank.
    assert _derive_title("tell me about").lower().startswith("tell me about") or _derive_title("tell me about") == "New Chat"


def test_placeholder_titles_are_recognized() -> None:
    # These (case-insensitively) are the only titles auto-rename will overwrite.
    for placeholder in ("New Chat", "new chat", "", "Untitled Chat"):
        assert placeholder.strip().lower() in _DEFAULT_TITLES
    # A real user title must never be treated as a placeholder.
    assert "database normalization" not in _DEFAULT_TITLES

"""Unit tests for greeting/question intent routing.

The classifier gates whether a message runs the full RAG pipeline, so its
precision matters: greetings must skip retrieval, but anything resembling a real
question must NOT be misrouted (which would silently drop grounding).
"""
from __future__ import annotations

import pytest

from app.services.agents.intent import INTENT_GREETING, INTENT_QUESTION, classify_intent


@pytest.mark.parametrize(
    "text",
    [
        "Hi",
        "hi",
        "Hello",
        "hello there",
        "Hey!",
        "good morning",
        "Good evening",
        "Thanks",
        "thank you so much",
        "thx",
        "ok",
        "cool",
        "how are you",
        "bye",
    ],
)
def test_greetings_are_greetings(text: str) -> None:
    assert classify_intent(text) == INTENT_GREETING


@pytest.mark.parametrize(
    "text",
    [
        "What is the Dandi March?",
        "Summarize Chapter 5",
        "explain photosynthesis",
        "tell me about the ede93 history document",
        "how do I reset my password",  # 'how' + length -> real question
        "hi, what is the dandi march",  # greeting word but carries a question
        "list the key findings",
        "describe the architecture",
        "Is the contract still valid?",
        "define entropy",
    ],
)
def test_questions_are_questions(text: str) -> None:
    assert classify_intent(text) == INTENT_QUESTION


def test_empty_is_question() -> None:
    # Empty / whitespace should fall through to the safe (full-pipeline) path.
    assert classify_intent("") == INTENT_QUESTION
    assert classify_intent("   ") == INTENT_QUESTION

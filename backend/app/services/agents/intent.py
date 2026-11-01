"""Lightweight, deterministic intent routing for the agent graph.

Simple greetings and small talk ("hi", "thanks", "good morning") should NOT
trigger the full retrieval + reasoning + citation pipeline. Detecting them with
a cheap rule — no LLM call, no embeddings — lets us answer conversationally and
instantly, and keeps retrieval focused on real document questions.

Deliberately conservative: anything that looks like a question (contains a
question mark, a question/instruction word, or is more than a few words) falls
through to the full RAG path, so we never skip retrieval for a real query.
"""
from __future__ import annotations

import re

INTENT_GREETING = "greeting"
INTENT_QUESTION = "question"

# Whole-message greetings / acknowledgements (after normalization).
_GREETING_PHRASES = {
    "hi", "hii", "hiya", "hey", "heya", "hello", "helo", "yo", "sup", "howdy",
    "greetings", "hi there", "hey there", "hello there",
    "good morning", "good afternoon", "good evening", "good day",
    "thanks", "thank you", "thanks a lot", "thank you so much", "thx", "ty",
    "cheers", "much appreciated", "appreciate it",
    "ok", "okay", "okey", "cool", "great", "nice", "awesome", "perfect", "got it",
    "bye", "goodbye", "see you", "see ya", "take care",
    "how are you", "how are you doing", "hows it going", "how is it going",
    "whats up", "what is up", "good night", "morning", "evening",
}

# First word is a clear greeting opener (e.g. "hey!", "hello 👋").
_GREETING_OPENERS = {
    "hi", "hii", "hiya", "hey", "heya", "hello", "helo", "yo", "howdy",
    "greetings", "thanks", "thank", "thx", "ty", "cheers", "bye", "goodbye",
}

# If any of these appear, it's a real request — never treat as small talk.
_QUESTION_MARKERS = {
    "what", "what's", "whats", "when", "where", "who", "whom", "why", "how",
    "which", "whose", "summarize", "summarise", "explain", "describe", "define",
    "list", "compare", "analyze", "analyse", "tell", "show", "find", "give",
    "outline", "detail", "elaborate", "who's", "can", "could", "would", "should",
    "is", "are", "do", "does", "did", "help",
}


def _normalize(text: str) -> str:
    # Lowercase, drop everything but letters/spaces, collapse whitespace.
    stripped = re.sub(r"[^a-z\s]", " ", text.lower())
    return re.sub(r"\s+", " ", stripped).strip()


def classify_intent(text: str) -> str:
    """Return ``"greeting"`` for small talk, otherwise ``"question"``."""
    raw = (text or "").strip()
    if not raw:
        return INTENT_QUESTION
    # A question mark almost always signals a real query.
    if "?" in raw:
        return INTENT_QUESTION

    norm = _normalize(text)
    if not norm:
        return INTENT_QUESTION

    words = norm.split()
    # Only short utterances can be small talk.
    if len(words) > 5:
        return INTENT_QUESTION

    if norm in _GREETING_PHRASES:
        return INTENT_GREETING

    # Short openers like "hey!" or "thanks so much" — as long as there's no
    # question/instruction word riding along ("hi, summarize chapter 5").
    if words[0] in _GREETING_OPENERS and not any(w in _QUESTION_MARKERS for w in words):
        return INTENT_GREETING

    return INTENT_QUESTION

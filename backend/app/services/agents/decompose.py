"""Multi-part question decomposition for the planner.

A single prompt often bundles several independent asks:

    "Difference between RAM and ROM, types of RAM and ROM,
     projects by Aditya Mishra, summarize Gandhara vs Mathura"

Retrieving once for that whole string blends unrelated topics into one weak
query and lets the strongest topic dominate. Instead we split it into
self-contained sub-questions and retrieve for each independently.

The LLM split is gated behind a cheap, deterministic heuristic so simple
single questions never pay for an extra model call.
"""
from __future__ import annotations

import re

# Cap so a pathological prompt can't fan out into dozens of retrieval runs.
MAX_TASKS = 6

DECOMPOSE_PROMPT = (
    "You break a user's request into independent, self-contained sub-questions "
    "for a document search engine.\n"
    "Rules:\n"
    "- Output ONE sub-question per line. No numbering, bullets, quotes, or commentary.\n"
    "- Each sub-question must stand alone: resolve pronouns and repeat the subject.\n"
    "- Split compound asks (e.g. 'types of RAM and ROM' becomes 'Types of RAM' and 'Types of ROM').\n"
    "- Do NOT invent topics the user did not ask about.\n"
    "- If the request is already a single question, output it unchanged on one line.\n\n"
    "Request:\n{text}"
)


def looks_multipart(text: str) -> bool:
    """Cheap check for whether a prompt bundles several distinct asks.

    Conservative on purpose: a lone conjunction ("difference between RAM and
    ROM") is NOT multi-part, but explicit separators (commas, newlines,
    semicolons) between clauses, or two or more question marks, are.
    """
    t = (text or "").strip()
    if not t:
        return False
    if t.count("?") >= 2:
        return True
    # Distinct clauses separated by punctuation the user used to enumerate asks.
    segments = re.split(r"[\n;,]+|\b(?:and then|as well as|also)\b", t)
    meaningful = [s for s in segments if len(s.strip().split()) >= 2]
    return len(meaningful) >= 2


def parse_subquestions(raw: str, original: str, *, max_tasks: int = MAX_TASKS) -> list[str]:
    """Parse the decomposer's line-per-question output into a clean task list.

    Strips numbering/bullets, drops blanks, de-duplicates case-insensitively,
    and falls back to the original prompt if parsing yields nothing usable.
    """
    seen: set[str] = set()
    tasks: list[str] = []
    for line in (raw or "").splitlines():
        cleaned = line.strip().lstrip("-•*0123456789.)( ").strip().strip('"')
        if len(cleaned.split()) < 2:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        tasks.append(cleaned)
        if len(tasks) >= max_tasks:
            break
    return tasks or [original.strip()]

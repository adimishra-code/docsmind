from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.core.exceptions import ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)


class PromptGuard:
    """Security and formatting pipeline for LLM prompts."""

    MAX_QUERY_LENGTH = 2000
    
    # Simple regex blocklist for common injection patterns
    INJECTION_PATTERNS = [
        re.compile(r"(?i)ignore\s+previous\s+instructions"),
        re.compile(r"(?i)ignore\s+all\s+instructions"),
        re.compile(r"(?i)you\s+are\s+now"),
        re.compile(r"(?i)forget\s+what\s+you\s+were\s+told"),
        re.compile(r"\[SYSTEM\]"),
        re.compile(r"<\|im_start\|>"),
    ]

    @classmethod
    def sanitize_query(cls, query: str) -> str:
        """Sanitize a user query against injections and normalize it."""
        if not query:
            return ""

        # 1. Unicode normalization
        query = unicodedata.normalize("NFKC", query)
        
        # 2. Length validation
        if len(query) > cls.MAX_QUERY_LENGTH:
            logger.warning("Query exceeded max length, truncating", length=len(query))
            query = query[:cls.MAX_QUERY_LENGTH]
            
        # 3. Regex filtering
        for pattern in cls.INJECTION_PATTERNS:
            if pattern.search(query):
                logger.warning("Potential prompt injection detected, stripping pattern", pattern=pattern.pattern)
                query = pattern.sub("", query)
                
        return query.strip()

    @classmethod
    def build_grounded_system_prompt(cls, chunks: list[dict[str, Any]]) -> str:
        """Build the grounded system prompt from retrieved context blocks."""
        context_blocks = []
        for i, chunk in enumerate(chunks, start=1):
            filename = chunk["payload"].get("filename") or "Unknown File"
            page = chunk["payload"].get("page_number") or "N/A"
            content = chunk["payload"]["content"]
            context_blocks.append(f"[{i}] (File: {filename}, Page: {page})\n{content}")

        context_string = "\n\n---\n\n".join(context_blocks)

        return (
            "You are an enterprise AI document assistant. Your task is to answer user queries truthfully and "
            "accurately using ONLY the text chunks enclosed in the context block below.\n\n"
            "Guidelines:\n"
            "1. Ground your answers strictly in the context. Do not extrapolate, hallucinate, or make up facts.\n"
            "2. If the context does not contain the answer, state: 'I cannot find the answer to this question in the uploaded documents.'\n"
            "3. Cite every sentence that relies on the context. Append bracketed numbers matching the context block indices (e.g. [1], [2]). "
            "Place citations directly after the matching sentences, before the ending punctuation.\n\n"
            "Context Blocks:\n"
            "--- START CONTEXT ---\n"
            f"{context_string}\n"
            "--- END CONTEXT ---"
        )
        
    @classmethod
    def format_user_message(cls, sanitized_query: str) -> str:
        """Wrap user query in XML tags to clearly separate instructions from user input."""
        return f"<query>\n{sanitized_query}\n</query>"

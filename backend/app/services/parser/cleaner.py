from __future__ import annotations

import re
import unicodedata


def normalize_whitespace(text: str) -> str:
    """Normalize excess spacing, line breaks, and whitespace tabs.

    Converts multiple spaces to single spaces and consolidates excess
    line endings to at most double newlines to split paragraphs cleanly.
    """
    if not text:
        return ""
    # Consolidate double newlines/paragraphs
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove excessive horizontal spaces
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def sanitize_text(text: str) -> str:
    """Clean common Unicode discrepancies, hyphens, and curly quotes."""
    if not text:
        return ""

    # Normalize Unicode characters to canonical decomposition
    text = unicodedata.normalize("NFKC", text)

    # Standardize curly single and double quotes
    quotes_map = {
        "“": '"', "”": '"', "„": '"', "‟": '"',
        "‘": "'", "’": "'", "‚": "'", "‛": "'",
    }
    for curly, straight in quotes_map.items():
        text = text.replace(curly, straight)

    # Fix word hyphenations split across line breaks (e.g., "docu-\nment" -> "document")
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)

    # Strip control characters except tab and newlines
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in ("\n", "\t"))

    return normalize_whitespace(text)

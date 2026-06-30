from __future__ import annotations

import re
from typing import Any
import tiktoken

from app.core.exceptions import ValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Base Chunker Interface
# --------------------------------------------------------------------------- #
class Chunker:
    """Strategy interface for splitting document text into searchable chunks."""

    def split_text(self, text: str) -> list[dict[str, Any]]:
        """Split text into chunks.

        Returns a list of dicts:
        [{"content": "chunk text", "page_number": int | None, "metadata": dict}]
        """
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# Recursive Character Chunker
# --------------------------------------------------------------------------- #
class RecursiveCharacterChunker(Chunker):
    """Splits text recursively by prioritized separators.

    Separators: Paragraphs (\\n\\n), lines (\\n), spaces ( ), empty strings ("").
    This preserves natural paragraphs and sentence blocks.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        if self.chunk_overlap >= self.chunk_size:
            raise ValidationError("Chunk overlap must be smaller than chunk size.")

    def split_text(self, text: str) -> list[dict[str, Any]]:
        if not text:
            return []

        # Parse text into page segments to maintain page numbers
        pages = self._parse_pages(text)
        chunks = []

        for page_num, page_text in pages:
            if not page_text.strip():
                continue
            
            # Split the page text recursively
            splits = self_split(page_text, self.chunk_size, self.chunk_overlap)
            for s_idx, split_content in enumerate(splits):
                chunks.append({
                    "content": split_content,
                    "page_number": page_num,
                    "metadata": {
                        "strategy": "recursive_character",
                        "index_on_page": s_idx,
                    }
                })
        return chunks

    def _parse_pages(self, text: str) -> list[tuple[int, str]]:
        """Parse fitz annotated page markers (e.g. --- PAGE 1 ---)."""
        pattern = r"--- PAGE (\d+) ---\n"
        matches = list(re.finditer(pattern, text))
        
        if not matches:
            return [(1, text)]

        pages = []
        for i, match in enumerate(matches):
            page_num = int(match.group(1))
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            pages.append((page_num, text[start:end]))
        return pages


def self_split(text: str, max_chars: int, overlap: int) -> list[str]:
    """Helper method to recursively divide a string by natural separators."""
    if len(text) <= max_chars:
        return [text]

    separators = ["\n\n", "\n", " ", ""]
    best_separator = ""
    for sep in separators:
        if sep == "":
            best_separator = ""
            break
        if sep in text:
            best_separator = sep
            break

    if best_separator == "":
        # Hard split by character indices
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start : start + max_chars])
            start += max_chars - overlap
        return chunks

    splits = text.split(best_separator)
    chunks = []
    current_chunk = []
    current_length = 0

    for split in splits:
        split_len = len(split) + len(best_separator)
        if current_length + split_len > max_chars:
            if current_chunk:
                chunks.append(best_separator.join(current_chunk))
            
            # Backtrack to add overlap context
            overlap_chars = 0
            overlap_chunk = []
            for item in reversed(current_chunk):
                item_len = len(item) + len(best_separator)
                if overlap_chars + item_len <= overlap:
                    overlap_chunk.insert(0, item)
                    overlap_chars += item_len
                else:
                    break

            current_chunk = overlap_chunk
            current_length = sum(len(x) + len(best_separator) for x in current_chunk)

        current_chunk.append(split)
        current_length += split_len

    if current_chunk:
        chunks.append(best_separator.join(current_chunk))

    return chunks


# --------------------------------------------------------------------------- #
# Token Based Chunker
# --------------------------------------------------------------------------- #
class TokenBasedChunker(Chunker):
    """Splits text based on tiktoken token counts instead of character counts."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64, encoding_name: str = "cl100k_base") -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.encoder = tiktoken.get_encoding(encoding_name)

        if self.chunk_overlap >= self.chunk_size:
            raise ValidationError("Chunk overlap must be smaller than chunk size.")

    def split_text(self, text: str) -> list[dict[str, Any]]:
        if not text:
            return []

        # Parse text into page segments to retain page numbers
        # We reuse the helper method from RecursiveCharacterChunker
        pages = RecursiveCharacterChunker()._parse_pages(text)
        chunks = []

        for page_num, page_text in pages:
            tokens = self.encoder.encode(page_text)
            if not tokens:
                continue

            start = 0
            s_idx = 0
            while start < len(tokens):
                end = start + self.chunk_size
                chunk_tokens = tokens[start:end]
                chunk_content = self.encoder.decode(chunk_tokens)
                
                chunks.append({
                    "content": chunk_content,
                    "page_number": page_num,
                    "metadata": {
                        "strategy": "token_based",
                        "index_on_page": s_idx,
                        "token_count": len(chunk_tokens),
                    }
                })
                start += self.chunk_size - self.chunk_overlap
                s_idx += 1
                
                # Check for infinite loops if overlap calculations yield 0 step increment
                if self.chunk_size <= self.chunk_overlap:
                    break
        return chunks


# --------------------------------------------------------------------------- #
# Markdown Aware Chunker
# --------------------------------------------------------------------------- #
class MarkdownAwareChunker(Chunker):
    """Splits Markdown documents maintaining section boundaries.

    It detects markdown headers (# H1, ## H2) and keeps sections
    contained together unless they exceed maximum limits.
    """

    def __init__(self, max_chars: int = 1000) -> None:
        self.max_chars = max_chars

    def split_text(self, text: str) -> list[dict[str, Any]]:
        if not text:
            return []

        # Split on headers (# H1, ## H2, etc.)
        pattern = r"(^#+\s+.*$)"
        lines = text.splitlines()
        
        sections = []
        current_section = []
        current_len = 0

        for line in lines:
            if re.match(pattern, line):
                if current_section:
                    sections.append("\n".join(current_section))
                    current_section = []
                    current_len = 0
            
            line_len = len(line)
            if current_len + line_len > self.max_chars:
                if current_section:
                    sections.append("\n".join(current_section))
                current_section = [line]
                current_len = line_len
            else:
                current_section.append(line)
                current_len += line_len + 1

        if current_section:
            sections.append("\n".join(current_section))

        chunks = []
        for s_idx, sec in enumerate(sections):
            chunks.append({
                "content": sec,
                "page_number": 1,  # Markdown files typically default to single page context
                "metadata": {
                    "strategy": "markdown_aware",
                    "index": s_idx,
                }
            })
        return chunks


# --------------------------------------------------------------------------- #
# Factory Provider
# --------------------------------------------------------------------------- #
def get_chunker(strategy: str, **kwargs: Any) -> Chunker:
    """Factory helper creating configured chunker instance."""
    strat = strategy.lower().strip()
    if strat == "recursive_character":
        return RecursiveCharacterChunker(
            chunk_size=kwargs.get("chunk_size", 512),
            chunk_overlap=kwargs.get("chunk_overlap", 64)
        )
    elif strat == "token_based":
        return TokenBasedChunker(
            chunk_size=kwargs.get("chunk_size", 512),
            chunk_overlap=kwargs.get("chunk_overlap", 64)
        )
    elif strat == "markdown_aware":
        return MarkdownAwareChunker(
            max_chars=kwargs.get("chunk_size", 1000)
        )
    else:
        # Default fallback
        return RecursiveCharacterChunker(
            chunk_size=kwargs.get("chunk_size", 512),
            chunk_overlap=kwargs.get("chunk_overlap", 64)
        )

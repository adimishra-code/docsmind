from __future__ import annotations

from datetime import datetime, UTC
import re
from typing import Any

from app.models.document import Document
from app.services.parser.parsers import detect_document_language


class MetadataExtractor:
    """Consolidates document properties, language details, and parser telemetry."""

    def extract(
        self,
        doc_obj: Document,
        parsed_text: str,
        parser_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        # 1. Detect language from text sample
        language = detect_document_language(parsed_text)

        # 2. Extract structural elements from text blocks (heuristics)
        title = self._heuristically_extract_title(parsed_text, doc_obj.filename)
        author = self._heuristically_extract_author(parsed_text, parser_metadata)
        keywords = self._heuristically_extract_keywords(parsed_text)

        # 3. Compile unified metadata schema
        consolidated = {
            "title": title,
            "author": author,
            "language": language,
            "keywords": keywords,
            "file_size": doc_obj.file_size,
            "upload_date": datetime.now(UTC).isoformat(),
            "document_type": doc_obj.file_type.lower().strip("."),
            
            # Metadata compiled by sub-parsers (tables, pages count, ocr logs)
            "pages": parser_metadata.get("pages") or parser_metadata.get("slides_count") or 1,
            "headings": parser_metadata.get("headings", []),
            "tables": parser_metadata.get("tables", []),
            "ocr_applied": parser_metadata.get("ocr_applied", False),
        }

        # Merge any pre-existing custom metadata
        if doc_obj.doc_metadata:
            consolidated.update(doc_obj.doc_metadata)

        return consolidated

    def _heuristically_extract_title(self, text: str, filename: str) -> str:
        """Inspect the first few lines of text to find a valid title, falling back to filename."""
        if not text:
            return filename

        # Read first 3 lines
        lines = [line.strip() for line in text.splitlines()[:5] if line.strip()]
        for line in lines:
            # Skip page headers or PAGE indicators
            if "PAGE" in line or line.startswith("---"):
                continue
            # If line is short and uppercase, it's likely a title
            if 10 < len(line) < 100:
                return line

        # Strip file extension for default title fallback
        return re.sub(r"\.[^.]+$", "", filename).replace("_", " ").title()

    def _heuristically_extract_author(self, text: str, parser_metadata: dict[str, Any]) -> str:
        """Look for author signatures or metadata attributes."""
        # Check standard metadata fields returned by PDF/DOCX parses if available
        if "author" in parser_metadata:
            return str(parser_metadata["author"])

        # Check top lines of text for "Author: " prefix
        lines = text.splitlines()[:20]
        for line in lines:
            match = re.search(r"^\s*author\s*:\s*(.*)$", line, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "Unknown"

    def _heuristically_extract_keywords(self, text: str) -> list[str]:
        """Simple extraction of top nouns/keywords from the text (heuristics)."""
        if not text:
            return []
        
        # Strip signs and convert to lower case
        words = re.findall(r"\b[a-zA-Z]{5,15}\b", text.lower())
        
        # Stopwords filter
        stopwords = {
            "about", "above", "after", "again", "against", "all", "am", "an", "and",
            "any", "are", "aren", "as", "at", "be", "because", "been", "before",
            "being", "below", "between", "both", "but", "by", "can", "cannot",
            "could", "did", "do", "does", "doing", "down", "during", "each",
            "few", "for", "from", "further", "had", "has", "have", "having",
            "he", "her", "here", "hers", "herself", "him", "himself", "his",
            "how", "if", "in", "into", "is", "isn", "it", "its", "itself",
            "me", "more", "most", "must", "my", "myself", "no", "nor", "not",
            "of", "off", "on", "once", "only", "or", "other", "ought", "our",
            "ours", "ourselves", "out", "over", "own", "same", "she", "should",
            "so", "some", "such", "than", "that", "the", "their", "theirs",
            "them", "themselves", "then", "there", "these", "they", "this",
            "those", "through", "to", "too", "under", "until", "up", "very",
            "was", "we", "were", "what", "when", "where", "which", "while",
            "who", "whom", "why", "with", "would", "you", "your", "yours",
            "yourself", "yourselves", "document", "chapter", "section", "page",
        }
        
        filtered = [w for w in words if w not in stopwords]
        
        # Count frequencies
        freq: dict[str, int] = {}
        for w in filtered:
            freq[w] = freq.get(w, 0) + 1
            
        # Get top 5 sorted by frequency
        sorted_keys = sorted(freq, key=freq.get, reverse=True)  # type: ignore[arg-type]
        return sorted_keys[:5]

from __future__ import annotations

import re
from typing import Any
import uuid

from sqlalchemy import select

import app.db.session as db_session
from app.models.document import Document
from app.core.logging import get_logger

logger = get_logger(__name__)


class CitationEngine:
    """Parses text responses to build verified source attribution citation objects."""

    async def extract_citations(
        self,
        text: str,
        retrieved_chunks: list[dict[str, Any]],
    ) -> tuple[str, list[dict[str, Any]]]:
        """Parse text for bracketed index tags and compile citation profiles."""
        if not text or not retrieved_chunks:
            return text, []

        logger.info("Extracting citations from response text")

        # 1. Fetch document filenames in a single query to translate IDs
        doc_ids = {uuid.UUID(c["payload"]["document_id"]) for c in retrieved_chunks}
        doc_names: dict[uuid.UUID, str] = {}
        
        if doc_ids:
            async with db_session.AsyncSessionLocal() as session:
                stmt = select(Document.id, Document.filename).where(Document.id.in_(doc_ids))
                result = await session.execute(stmt)
                for d_id, fname in result.all():
                    doc_names[d_id] = fname

        # Inject filenames into chunks in-memory
        for chunk in retrieved_chunks:
            d_id = uuid.UUID(chunk["payload"]["document_id"])
            chunk["payload"]["filename"] = doc_names.get(d_id, "Unknown Document")

        # 2. Extract unique citation index markers [N]
        raw_tags = re.findall(r"\[(\d+)\]", text)
        
        # Deduplicate tags to prevent duplicate citation exports while maintaining order
        referenced_indices = []
        for tag in raw_tags:
            idx = int(tag)
            if idx not in referenced_indices:
                referenced_indices.append(idx)

        # 3. Construct unified citation profiles
        citations = []
        for citation_no, idx in enumerate(referenced_indices, start=1):
            if 1 <= idx <= len(retrieved_chunks):
                chunk = retrieved_chunks[idx - 1]
                
                # Retrieve original excerpt (pre parent-context expansion if applicable)
                excerpt = chunk["payload"].get("original_content") or chunk["payload"]["content"]
                
                citations.append({
                    "citation_index": citation_no,
                    "document_name": chunk["payload"]["filename"],
                    "document_id": chunk["payload"]["document_id"],
                    "page_number": chunk["payload"]["page_number"],
                    "chunk_id": str(chunk["chunk_id"]),
                    "confidence_score": round(chunk.get("rerank_score") or chunk["score"], 4),
                    "supporting_excerpt": excerpt.strip(),
                })

        return text, citations

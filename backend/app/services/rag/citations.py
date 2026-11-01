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
        
        # Deduplicate and sort tags so citations are cleanly ordered
        referenced_indices = sorted({int(tag) for tag in raw_tags if tag.isdigit()})

        # 3. Construct unified citation profiles
        citations = []
        for idx in referenced_indices:
            if 1 <= idx <= len(retrieved_chunks):
                chunk = retrieved_chunks[idx - 1]
                
                # Retrieve original excerpt (pre parent-context expansion if applicable)
                excerpt = chunk["payload"].get("original_content") or chunk["payload"]["content"]
                clean_excerpt = re.sub(r"^\[Document:[^\]]+\]\s*", "", excerpt).strip()
                
                citations.append({
                    "citation_index": idx,
                    "index": idx,
                    "document_name": chunk["payload"]["filename"],
                    "document_id": chunk["payload"]["document_id"],
                    "page_number": chunk["payload"]["page_number"],
                    "chunk_id": str(chunk["chunk_id"]),
                    "confidence_score": round(chunk.get("rerank_score") or chunk["score"], 4),
                    "supporting_excerpt": clean_excerpt,
                })

        return text, citations

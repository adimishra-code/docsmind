from __future__ import annotations

from typing import Any
import uuid

from app.core.logging import get_logger
from app.services.rag.bm25_manager import BM25IndexManager, simple_tokenizer

logger = get_logger(__name__)


class SparseSearcher:
    """lexical search engine utilizing BM25 Okapi calculations."""

    def __init__(self, index_manager: BM25IndexManager):
        self.index_manager = index_manager

    async def search(
        self,
        query: str,
        user_id: uuid.UUID,
        *,
        limit: int = 10,
        document_ids: list[uuid.UUID] | None = None,
    ) -> list[dict[str, Any]]:
        """Query user chunks lexical relevance, isolated by tenancy and document scopes."""
        logger.info("Executing BM25 sparse search", user_id=user_id, query=query)
        tokenized_query = simple_tokenizer(query)
        if not tokenized_query:
            return []

        bm25, metadata = await self.index_manager.get_or_build_index(user_id)

        if not metadata or bm25 is None:
            logger.info("No documents found for sparse search scope")
            return []

        scores = bm25.get_scores(tokenized_query)

        scored_candidates = []
        for meta, score in zip(metadata, scores, strict=True):
            if score > 0.0:
                if document_ids and meta.get("document_id"):
                    if meta["document_id"] not in {str(did) for did in document_ids}:
                        continue
                scored_candidates.append({
                    "chunk_id": uuid.UUID(meta["chunk_id"]),
                    "score": float(score),
                    "payload": {
                        "document_id": meta["document_id"],
                        "chunk_index": meta["chunk_index"],
                        "page_number": meta["page_number"],
                        "content": meta["content"],
                    }
                })

        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates[:limit]

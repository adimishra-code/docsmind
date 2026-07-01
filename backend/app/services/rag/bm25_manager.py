from __future__ import annotations

import json
from typing import Any
import uuid

from rank_bm25 import BM25Okapi
from redis.asyncio import Redis
from sqlalchemy import select

import app.db.session as db_session
from app.models.document import Document, DocumentChunk
from app.core.logging import get_logger

logger = get_logger(__name__)


def simple_tokenizer(text: str) -> list[str]:
    """Tokenize a string into lowercase alphanumeric words."""
    import re
    return re.findall(r"\b[a-zA-Z0-9]{2,20}\b", text.lower())


class BM25IndexManager:
    """Manages building, caching, and retrieving BM25 indexes.

    Caches the tokenized corpus in Redis (for persistence across restarts)
    and the fitted BM25Okapi instance in memory (avoids O(n) rebuild per query).
    """

    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self.ttl = 3600
        self._in_memory: dict[str, tuple[BM25Okapi, list[dict[str, Any]]]] = {}

    async def get_or_build_index(self, user_id: uuid.UUID) -> tuple[BM25Okapi, list[dict[str, Any]]]:
        """Return a fitted BM25Okapi instance + metadata for the user.

        Checks in-memory cache first, then Redis, then rebuilds from DB.
        """
        uid_str = str(user_id)
        cached = self._in_memory.get(uid_str)
        if cached is not None:
            logger.debug("BM25 in-memory index hit", user_id=user_id)
            return cached

        corpus, metadata = await self._get_or_build_corpus(user_id)
        bm25 = BM25Okapi(corpus)
        result = (bm25, metadata)
        self._in_memory[uid_str] = result
        return result

    async def _get_or_build_corpus(self, user_id: uuid.UUID) -> tuple[list[list[str]], list[dict[str, Any]]]:
        """Fetch tokenized corpus from Redis, or rebuild from DB if missing."""
        cache_key = f"bm25_corpus:{user_id}"

        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                logger.debug("BM25 corpus cache hit", user_id=user_id)
                data = json.loads(cached_data)
                return data["corpus"], data["metadata"]
        except Exception:
            logger.warning("Redis cache error, falling back to DB build", exc_info=True)

        logger.info("BM25 corpus cache miss, rebuilding from DB", user_id=user_id)

        async with db_session.AsyncSessionLocal() as session:
            stmt = select(DocumentChunk).join(Document).where(Document.user_id == user_id)
            result = await session.execute(stmt)
            chunks = list(result.scalars().all())

        corpus = []
        metadata = []

        for chunk in chunks:
            corpus.append(simple_tokenizer(chunk.content))
            metadata.append({
                "chunk_id": str(chunk.id),
                "document_id": str(chunk.document_id),
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "content": chunk.content,
            })

        if corpus:
            try:
                payload = json.dumps({"corpus": corpus, "metadata": metadata})
                await self.redis.setex(cache_key, self.ttl, payload)
            except Exception:
                logger.warning("Failed to cache BM25 corpus to Redis", exc_info=True)

        return corpus, metadata

    async def invalidate(self, user_id: uuid.UUID) -> None:
        """Invalidate both in-memory and Redis caches when documents change."""
        uid_str = str(user_id)
        self._in_memory.pop(uid_str, None)
        cache_key = f"bm25_corpus:{user_id}"
        try:
            await self.redis.delete(cache_key)
            logger.info("Invalidated BM25 caches", user_id=user_id)
        except Exception:
            pass

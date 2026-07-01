"""Embedding providers with singleton client and LRU cache."""
from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
import hashlib
from collections import OrderedDict
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.services.rag.llm_client import get_llm_client

logger = get_logger(__name__)


class LRUCache:
    """Simple thread-safe LRU cache for embedding results."""

    def __init__(self, maxsize: int = 1000) -> None:
        self.maxsize = maxsize
        self._cache: OrderedDict[str, list[float]] = OrderedDict()

    def _make_key(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> list[float] | None:
        key = self._make_key(text)
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def put(self, text: str, embedding: list[float]) -> None:
        key = self._make_key(text)
        self._cache[key] = embedding
        self._cache.move_to_end(key)
        if len(self._cache) > self.maxsize:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        self._cache.clear()


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        pass


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or settings.EMBEDDING_MODEL
        self.client = get_llm_client()
        self.batch_size = 2048
        self._cache = LRUCache(maxsize=500)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        uncached: list[tuple[int, str]] = []
        results: list[list[float] | None] = [None] * len(texts)

        for i, t in enumerate(texts):
            cached = self._cache.get(t)
            if cached is not None:
                results[i] = cached
            else:
                uncached.append((i, t))

        if not uncached:
            return [r for r in results if r is not None]

        uncached_texts = [t for _, t in uncached]
        batches = [uncached_texts[i:i + self.batch_size] for i in range(0, len(uncached_texts), self.batch_size)]
        embeddings = []

        async def _embed_batch(batch_texts: list[str], retries: int = 3) -> list[list[float]]:
            backoff = 1.0
            for attempt in range(retries):
                try:
                    response = await self.client.embeddings.create(input=batch_texts, model=self.model)
                    return [item.embedding for item in response.data]
                except Exception as exc:
                    if attempt == retries - 1:
                        logger.exception("Failed to generate OpenAI embeddings after retries")
                        raise exc
                    logger.warning("OpenAI embedding request failed. Retrying...", attempt=attempt + 1, backoff=backoff, error=str(exc))
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
            return []

        tasks = [_embed_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks)

        for batch_res in batch_results:
            embeddings.extend(batch_res)

        for (idx, text), emb in zip(uncached, embeddings):
            results[idx] = emb
            self._cache.put(text, emb)

        return [r for r in results if r is not None]

    async def embed_query(self, text: str) -> list[float]:
        cached = self._cache.get(text)
        if cached is not None:
            return cached
        response = await self.client.embeddings.create(input=[text], model=self.model)
        embedding = response.data[0].embedding
        self._cache.put(text, embedding)
        return embedding

    def clear_cache(self) -> None:
        self._cache.clear()


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.EMBEDDING_MODEL
        logger.info("Initializing local SentenceTransformer model", model=self.model_name)
        self._model: Any = None

    @property
    def model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = await asyncio.to_thread(self._encode_sync, texts)
        return [list(map(float, vec)) for vec in embeddings]

    async def embed_query(self, text: str) -> list[float]:
        embeddings = await asyncio.to_thread(self._encode_sync, [text])
        return list(map(float, embeddings[0]))

    def _encode_sync(self, texts: list[str]) -> Any:
        return self.model.encode(texts, show_progress_bar=False)


def get_embedding_provider() -> BaseEmbeddingProvider:
    provider_type = settings.EMBEDDING_PROVIDER.lower().strip()
    if provider_type == "openai":
        return OpenAIEmbeddingProvider()
    elif provider_type in ("sentence_transformers", "local", "bge", "instructor"):
        return LocalEmbeddingProvider()
    else:
        logger.error("Unknown embedding provider configured. Falling back to OpenAI.", provider=provider_type)
        return OpenAIEmbeddingProvider()

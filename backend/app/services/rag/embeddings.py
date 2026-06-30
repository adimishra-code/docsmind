from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from typing import Any

from openai import AsyncOpenAI
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Base Embedding Provider Contract
# --------------------------------------------------------------------------- #
class BaseEmbeddingProvider(ABC):
    """Abstract interface defining the contract for document and query embedding generators."""

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate high-dimensional vectors for a list of document strings."""
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Generate a high-dimensional vector representing a search query."""
        pass


# --------------------------------------------------------------------------- #
# OpenAI Embedding Provider
# --------------------------------------------------------------------------- #
class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Generates embeddings using OpenAI API (e.g. text-embedding-3-small)."""

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or settings.EMBEDDING_MODEL
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self.batch_size = 2048

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        # Split into batches to prevent payload size errors
        batches = [texts[i : i + self.batch_size] for i in range(0, len(texts), self.batch_size)]
        embeddings: list[list[float]] = []

        async def _embed_batch(batch_texts: list[str], retries: int = 3) -> list[list[float]]:
            backoff = 1.0
            for attempt in range(retries):
                try:
                    response = await self.client.embeddings.create(
                        input=batch_texts,
                        model=self.model,
                    )
                    return [item.embedding for item in response.data]
                except Exception as exc:
                    if attempt == retries - 1:
                        logger.exception("Failed to generate OpenAI embeddings after retries")
                        raise exc
                    logger.warning(
                        "OpenAI embedding request failed. Retrying...",
                        attempt=attempt + 1,
                        backoff=backoff,
                        error=str(exc),
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
            return []

        # Execute batches concurrently
        tasks = [_embed_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks)

        for batch_res in results:
            embeddings.extend(batch_res)

        return embeddings

    async def embed_query(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(
            input=[text],
            model=self.model,
        )
        return response.data[0].embedding


# --------------------------------------------------------------------------- #
# Local SentenceTransformers / BGE Provider
# --------------------------------------------------------------------------- #
class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Generates embeddings locally using SentenceTransformers (BGE/Instructor) models."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.EMBEDDING_MODEL
        logger.info("Initializing local SentenceTransformer model", model=self.model_name)
        # Load model lazily
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        
        # SentenceTransformers encode is CPU/GPU heavy and synchronous.
        # Offload to a worker thread to keep the main asyncio event loop responsive.
        embeddings = await asyncio.to_thread(self._encode_sync, texts)
        return [list(map(float, vec)) for vec in embeddings]

    async def embed_query(self, text: str) -> list[float]:
        embeddings = await asyncio.to_thread(self._encode_sync, [text])
        return list(map(float, embeddings[0]))

    def _encode_sync(self, texts: list[str]) -> Any:
        return self.model.encode(texts, show_progress_bar=False)


# --------------------------------------------------------------------------- #
# Factory Method
# --------------------------------------------------------------------------- #
def get_embedding_provider() -> BaseEmbeddingProvider:
    """Instantiate the active EmbeddingProvider based on configuration settings."""
    provider_type = settings.EMBEDDING_PROVIDER.lower().strip()
    if provider_type == "openai":
        return OpenAIEmbeddingProvider()
    elif provider_type in ("sentence_transformers", "local", "bge", "instructor"):
        return LocalEmbeddingProvider()
    else:
        logger.error("Unknown embedding provider configured. Falling back to OpenAI.", provider=provider_type)
        return OpenAIEmbeddingProvider()

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams, MatchAny

from app.core.config import settings
from app.core.logging import get_logger
from app.models.document import DocumentChunk

logger = get_logger(__name__)


class VectorStoreInterface(ABC):
    """Abstract interface for vector database operations."""
    
    @abstractmethod
    async def create_collection_if_not_exists(self, collection_name: str, vector_size: int) -> None:
        """Create a collection if it does not already exist."""
        pass
        
    @abstractmethod
    async def upsert_chunks(
        self,
        collection_name: str,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        user_id: uuid.UUID,
    ) -> None:
        """Upsert document chunks into the vector store."""
        pass
        
    @abstractmethod
    async def search_chunks(
        self,
        collection_name: str,
        query_vector: list[float],
        user_id: uuid.UUID,
        *,
        limit: int = 10,
        document_ids: list[uuid.UUID] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for nearest chunks matching the query vector."""
        pass
        
    @abstractmethod
    async def delete_by_document(
        self, collection_name: str, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Delete all vectors associated with a specific document."""
        pass


class QdrantAdapter(VectorStoreInterface):
    """Qdrant implementation of VectorStoreInterface using AsyncQdrantClient."""

    _shared_client: AsyncQdrantClient | None = None
    _shared_is_local: bool = False

    def __init__(self) -> None:
        if QdrantAdapter._shared_client is not None:
            self.client = QdrantAdapter._shared_client
            self._using_local = QdrantAdapter._shared_is_local
            return

        if os.getenv("PYTEST_CURRENT_TEST"):
            logger.info("Initializing SHARED in-memory Async Qdrant client for testing")
            QdrantAdapter._shared_client = AsyncQdrantClient(":memory:")
            QdrantAdapter._shared_is_local = False
            self.client = QdrantAdapter._shared_client
            return

        if settings.QDRANT_URL:
            try:
                client = AsyncQdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY,
                )
                logger.info("Initializing remote Async Qdrant client", url=settings.QDRANT_URL)
                QdrantAdapter._shared_client = client
                QdrantAdapter._shared_is_local = False
                self.client = client
                return
            except Exception:
                logger.warning("Qdrant remote URL unreachable, falling back to local disk",
                               url=settings.QDRANT_URL)

        os.makedirs(settings.QDRANT_STORAGE_PATH, exist_ok=True)
        logger.info("Initializing local disk Async Qdrant client", path=settings.QDRANT_STORAGE_PATH)
        QdrantAdapter._shared_client = AsyncQdrantClient(path=settings.QDRANT_STORAGE_PATH)
        QdrantAdapter._shared_is_local = True
        self.client = QdrantAdapter._shared_client
        self._using_local = True

    async def _fallback_to_local_if_needed(self, exc: Exception) -> bool:
        """If remote Qdrant failed in development, switch to embedded local disk."""
        if not getattr(self, "_using_local", False) and not settings.is_production:
            logger.warning(
                "Remote Qdrant connection failed, failing over to embedded local disk Qdrant",
                error=str(exc),
                path=settings.QDRANT_STORAGE_PATH,
            )
            os.makedirs(settings.QDRANT_STORAGE_PATH, exist_ok=True)
            if not getattr(QdrantAdapter, "_shared_is_local", False) or QdrantAdapter._shared_client is None:
                QdrantAdapter._shared_client = AsyncQdrantClient(path=settings.QDRANT_STORAGE_PATH)
                QdrantAdapter._shared_is_local = True
            self.client = QdrantAdapter._shared_client
            self._using_local = True
            return True
        return False

    async def create_collection_if_not_exists(
        self, collection_name: str, vector_size: int
    ) -> None:
        try:
            collections = await self.client.get_collections()
        except Exception as exc:
            if await self._fallback_to_local_if_needed(exc):
                collections = await self.client.get_collections()
            else:
                logger.exception("Failed to initialize vector collection", name=collection_name)
                raise exc

        try:
            exists = any(c.name == collection_name for c in collections.collections)
            if not exists:
                logger.info("Creating vector collection", name=collection_name, size=vector_size)
                await self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                )
        except Exception as exc:
            logger.exception("Failed to initialize vector collection", name=collection_name)
            raise exc

    async def upsert_chunks(
        self,
        collection_name: str,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        user_id: uuid.UUID,
    ) -> None:
        if not chunks:
            return

        points = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            point_id = str(chunk.id)
            # chunk_metadata may be None when created without explicit metadata
            # (e.g. in tests or when the ingestion pipeline omits it).
            meta = chunk.chunk_metadata or {}
            payload = {
                "user_id": str(user_id),
                "document_id": str(chunk.document_id),
                "filename": meta.get("filename", "Unknown"),
                "section": meta.get("section", ""),
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "content": chunk.content,
            }
            points.append(PointStruct(id=point_id, vector=embedding, payload=payload))

        try:
            await self.client.upsert(collection_name=collection_name, points=points)
            logger.info("Upserted points to vector database", count=len(points), name=collection_name)
        except Exception as exc:
            if await self._fallback_to_local_if_needed(exc):
                await self.create_collection_if_not_exists(collection_name, len(embeddings[0]) if embeddings else 1536)
                await self.client.upsert(collection_name=collection_name, points=points)
                logger.info("Upserted points to local vector database after failover", count=len(points), name=collection_name)
            else:
                logger.exception("Qdrant upsert failed", name=collection_name)
                raise exc

    async def search_chunks(
        self,
        collection_name: str,
        query_vector: list[float],
        user_id: uuid.UUID,
        *,
        limit: int = 10,
        document_ids: list[uuid.UUID] | None = None,
    ) -> list[dict[str, Any]]:
        must_conditions = [
            FieldCondition(
                key="user_id",
                match=MatchValue(value=str(user_id)),
            )
        ]

        if document_ids:
            must_conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchAny(any=[str(d) for d in document_ids]),
                )
            )

        query_filter = Filter(must=must_conditions)

        try:
            response = await self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
        except Exception as exc:
            if await self._fallback_to_local_if_needed(exc):
                response = await self.client.query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=limit,
                    with_payload=True,
                )
            else:
                logger.exception("Qdrant query execution failed", name=collection_name)
                raise exc
            
        return [
            {
                "chunk_id": uuid.UUID(r.id) if isinstance(r.id, str) else r.id,
                "score": r.score,
                "payload": r.payload or {},
            }
            for r in response.points
        ]

    async def delete_by_document(
        self, collection_name: str, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        query_filter = Filter(
            must=[
                FieldCondition(key="user_id", match=MatchValue(value=str(user_id))),
                FieldCondition(key="document_id", match=MatchValue(value=str(document_id))),
            ]
        )
        try:
            await self.client.delete(collection_name=collection_name, points_selector=query_filter)
            logger.info("Deleted vector points for document", document_id=document_id)
        except Exception as exc:
            if await self._fallback_to_local_if_needed(exc):
                await self.client.delete(collection_name=collection_name, points_selector=query_filter)
                logger.info("Deleted vector points for document on local disk", document_id=document_id)
            else:
                logger.exception("Qdrant delete by document failed", document_id=document_id)
                raise exc

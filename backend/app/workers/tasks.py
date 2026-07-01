from __future__ import annotations

import asyncio
from datetime import datetime, UTC
import time
import uuid
from typing import Any

from app.core.logging import get_logger
import app.db.session as db_session
from app.models.document import Document, DocumentChunk
from app.models.usage import UsageLog
from app.repositories.user import UserRepository  # to import repositories
from app.services.parser.chunker import get_chunker
from app.services.parser.cleaner import sanitize_text
from app.services.parser.metadata import MetadataExtractor
from app.services.parser.parsers import get_parser_for_file_type
from app.services.storage import get_storage_backend
from app.workers.celery_app import celery

logger = get_logger(__name__)


async def async_process_document(
    document_id_str: str,
    chunk_strategy: str = "recursive_character",
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> None:
    """Asynchronous implementation of document ingestion pipeline."""
    start_time = time.perf_counter()
    document_id = uuid.UUID(document_id_str)

    logger.info("Executing async document processing task", document_id=document_id)

    async with db_session.AsyncSessionLocal() as session:
        # 1. Fetch document record
        doc = await session.get(Document, document_id)
        if not doc:
            logger.error("Document not found in database", document_id=document_id)
            return

        # 2. Update status to 'processing'
        doc.status = "processing"
        await session.commit()
        await session.refresh(doc)

        try:
            # 3. Retrieve binary content from storage backend
            storage = get_storage_backend()
            file_bytes = await storage.download(doc.storage_path)

            # 4. Route file binary to appropriate format parser
            parser = get_parser_for_file_type(doc.file_type)
            raw_text, parser_metadata = parser.parse(file_bytes)

            # 5. Execute text normalization and sanitization
            clean_text = sanitize_text(raw_text)

            # 6. Extract document structures and metadata
            extractor = MetadataExtractor()
            final_metadata = extractor.extract(doc, clean_text, parser_metadata)

            # 7. Execute text chunk splitting strategy
            chunker = get_chunker(
                chunk_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            split_chunks = chunker.split_text(clean_text)

            # 8. Save chunks to database
            db_chunks = []
            for chunk_data in split_chunks:
                db_chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=chunk_data["metadata"]["index_on_page"],
                    content=chunk_data["content"],
                    page_number=chunk_data["page_number"],
                    chunk_metadata=chunk_data["metadata"],
                )
                session.add(db_chunk)
                db_chunks.append(db_chunk)

            # Flush to database so that chunk IDs are generated (needed for Qdrant points mapping)
            await session.flush()

            # 8.1 Generate embeddings and upsert to Qdrant vector store
            if db_chunks:
                from app.services.rag.embeddings import get_embedding_provider
                from app.services.rag.vector_store import QdrantAdapter
                from app.services.rag.token_manager import token_manager
                
                emb_provider = get_embedding_provider()
                # Retrieve vectors concurrently/in threads
                embeddings = await emb_provider.embed_documents([c.content for c in db_chunks])
                
                if embeddings:
                    vector_size = len(embeddings[0])
                    vector_store = QdrantAdapter()
                    await vector_store.create_collection_if_not_exists("document_chunks", vector_size)
                    
                    # Upload points to Qdrant
                    await vector_store.upsert_chunks(
                        "document_chunks", db_chunks, embeddings, doc.user_id
                    )
                    
                    # Update DB records with vector database reference id
                    for chunk in db_chunks:
                        chunk.embedding_id = str(chunk.id)

            # 9. Update document metadata and completion status
            doc.status = "completed"
            doc.doc_metadata = final_metadata
            await session.commit()

            # 9.5 Invalidate BM25 cache
            from app.db.redis import redis_client
            from app.services.rag.bm25_manager import BM25IndexManager
            await BM25IndexManager(redis_client).invalidate(doc.user_id)

            # 10. Record telemetry analytics log
            processing_time_ms = int((time.perf_counter() - start_time) * 1000)
            usage_log = UsageLog(
                user_id=doc.user_id,
                action="file_upload",
                token_count=token_manager.count_tokens(clean_text),
                latency_ms=processing_time_ms,
                cost=0.0,  # locally processed cost is 0
                extra_info={
                    "chunks_count": len(db_chunks),
                    "strategy": chunk_strategy,
                    "ocr_applied": final_metadata.get("ocr_applied", False),
                },
            )
            session.add(usage_log)
            await session.commit()

            logger.info(
                "Document ingestion pipeline completed successfully",
                document_id=document_id,
                duration_ms=processing_time_ms,
                chunks_created=len(db_chunks),
            )

        except Exception as exc:
            # 11. Handle execution exceptions, mark as failed, and capture stack trace
            logger.exception("Ingestion pipeline failed", document_id=document_id, error=str(exc))
            await session.rollback()
            
            # Fetch document again in a new transaction context to write the error status
            doc = await session.get(Document, document_id)
            if doc:
                doc.status = "failed"
                doc.error_message = str(exc)
                await session.commit()


def run_async(coro) -> Any:
    """Run an async coroutine, handling active event loops gracefully.

    If an event loop is already running (e.g., in a test suite or web thread),
    we execute the coroutine in a separate thread to prevent nested event loop issues.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, safe to run directly
        return asyncio.run(coro)
    else:
        # Loop is active, execute in a thread executor to bypass nesting
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()


@celery.task(name="app.workers.tasks.process_document_task")
def process_document_task(
    document_id_str: str,
    chunk_strategy: str = "recursive_character",
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> None:
    """Synchronous Celery task wrapper that runs the async processing pipeline."""
    run_async(
        async_process_document(
            document_id_str=document_id_str,
            chunk_strategy=chunk_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    )

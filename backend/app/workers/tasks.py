from __future__ import annotations

import asyncio
from datetime import datetime, UTC
import re
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

# ---------------------------------------------------------------------------
# Section heading detection
# ---------------------------------------------------------------------------
# Vocabulary of common section names in CVs, research papers, and technical
# documents.  When a chunk's first content line matches any of these (case-
# insensitively), it is tagged as that section's heading and the label is
# carried forward to every subsequent chunk in the same section.
_KNOWN_SECTION_HEADINGS: frozenset[str] = frozenset({
    # CV / Resume
    "projects", "project", "experience", "work experience",
    "professional experience", "employment", "employment history",
    "education", "academic background", "academic qualifications",
    "skills", "technical skills", "core competencies",
    "achievements", "accomplishments", "highlights",
    "publications", "research", "summary", "professional summary",
    "objective", "career objective", "profile", "about", "about me",
    "certifications", "certification", "languages", "interests",
    "hobbies", "references", "contact", "contact information",
    "awards", "volunteer", "volunteer work", "courses", "training",
    "internship", "internships", "extracurricular", "activities",
    "personal projects", "side projects", "open source",
    # Academic
    "abstract", "introduction", "related work", "background",
    "literature review", "methodology", "methods",
    "experimental setup", "experiments", "results", "findings",
    "discussion", "conclusion", "conclusions", "future work",
    "references", "bibliography", "appendix", "acknowledgements",
    "acknowledgments", "supplementary material", "notation",
    # Technical / documentation
    "overview", "architecture", "design", "installation", "setup",
    "usage", "quick start", "getting started", "configuration",
    "api reference", "api", "troubleshooting", "faq",
    "requirements", "prerequisites", "dependencies", "examples",
    "notes", "changelog", "roadmap", "contributing", "license",
    "security", "performance", "deployment", "testing",
    # Generic structure
    "description", "details", "information", "list", "index",
    "table of contents", "scope", "purpose", "objectives",
})

# Numbered-section pattern: "1. Introduction", "2.1 Methods", etc.
_NUMBERED_SECTION_RE = re.compile(
    r"^\d+(?:\.\d+)*\.?\s+([A-Z][A-Za-z &\-/]{2,60})$"
)


def _detect_section_heading(text: str) -> str | None:
    """Return the section heading if this chunk's first content line is one.

    Checks three signals in order:
      1. Known vocabulary match (case-insensitive) — highest precision.
      2. ALL-CAPS short line — catches CONTRACT / DOCUMENT style headings.
      3. Numbered section "2. Methodology" pattern — research papers, manuals.

    Only the *first non-empty, non-prefix* line is inspected so that heading
    detection never accidentally fires on body text deeper in the chunk.
    """
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        # Skip the injected context-prefix line: "[Document: …]"
        if stripped.startswith("[") and stripped.endswith("]"):
            continue
        # --- Signal 1: known vocabulary ---
        if stripped.lower() in _KNOWN_SECTION_HEADINGS:
            return stripped
        # --- Signal 2: ALL-CAPS line (2-8 words, no sentence punctuation) ---
        words = stripped.split()
        if (
            2 <= len(words) <= 8
            and stripped == stripped.upper()
            and stripped[-1:] not in ".!?,;:"
            and any(c.isalpha() for c in stripped)
        ):
            return stripped.title()
        # --- Signal 3: numbered section header ---
        # Only accept if the extracted text is a *known* section name so that
        # numbered list items ("2. AI Chatbot", "3. E-commerce Website") are NOT
        # mistaken for document sections ("2. Methodology", "3.1 Results").
        m = _NUMBERED_SECTION_RE.match(stripped)
        if m:
            heading_text = m.group(1).strip()
            if heading_text.lower() in _KNOWN_SECTION_HEADINGS:
                return heading_text
        # First real content line is not a heading — stop looking.
        break
    return None


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
            # Track the most recently seen section heading so every chunk in a
            # section carries its name — not just the chunk that contains the
            # heading line.  Without this carry-forward, chunks 2…N of a
            # "Projects" section have no indication they belong to "Projects",
            # making them invisible to BM25 queries like "projects of Aditya".
            current_section: str = ""

            for global_chunk_idx, chunk_data in enumerate(split_chunks):
                meta = chunk_data.get("metadata", {})
                title = doc.filename or "Unknown Document"
                raw_content: str = chunk_data["content"]

                # Detect heading in THIS chunk (chunker metadata → then heuristic).
                detected_heading = (
                    meta.get("heading")
                    or meta.get("section")
                    or _detect_section_heading(raw_content)
                )
                if detected_heading:
                    current_section = detected_heading

                # Use the live section or carry the last known one forward.
                section: str = current_section

                context_prefix = f"[Document: {title}"
                if section:
                    context_prefix += f", Section: {section}"
                context_prefix += "]\n\n"

                enriched_content = context_prefix + raw_content

                # Persist section into chunk metadata so Qdrant payloads and
                # adjacent-chunk re-fetches can surface it to the LLM.
                meta["filename"] = title
                if section:
                    meta["section"] = section

                db_chunk = DocumentChunk(
                    document_id=doc.id,
                    # Use a document-global index (not per-page) so adjacent-chunk
                    # enrichment correctly fetches neighbours by (doc_id, index±1).
                    # Previously used meta["index_on_page"] which resets to 0 for
                    # every page, making the DB lookup ambiguous.
                    chunk_index=global_chunk_idx,
                    content=enriched_content,
                    page_number=chunk_data.get("page_number", 1),
                    chunk_metadata=meta,
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


_worker_loop = None
_worker_thread = None

def _start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def run_async(coro) -> Any:
    """Run an async coroutine, handling active event loops gracefully.

    If an event loop is already running (e.g., in a test suite or web thread),
    we execute the coroutine in a separate thread to prevent nested event loop issues.
    For Celery workers, it maintains a persistent background event loop to reuse
    SQLAlchemy and Redis connection pools efficiently.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        # Loop is active, execute in a one-off thread executor to bypass nesting
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()

    global _worker_loop, _worker_thread
    if _worker_loop is None:
        import threading
        _worker_loop = asyncio.new_event_loop()
        _worker_thread = threading.Thread(target=_start_loop, args=(_worker_loop,), daemon=True)
        _worker_thread.start()
    
    future = asyncio.run_coroutine_threadsafe(coro, _worker_loop)
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

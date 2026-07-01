from __future__ import annotations

import pathlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from fastapi.responses import StreamingResponse
import io

from app.api.deps import CurrentUserDep, DocRepoDep
from app.core.exceptions import NotFoundError, ValidationError
from app.models.document import Document
from app.schemas.document import DocumentListResponse, DocumentResponse, DocumentStatusResponse
from app.services.storage import get_storage_backend
from app.workers.tasks import process_document_task

router = APIRouter()

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".csv", ".txt", ".md", ".xlsx", ".xls", ".html", ".htm", ".rtf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a new document",
)
async def upload_document(
    doc_repo: DocRepoDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(...),
    chunk_size: int = Form(512),
    chunk_overlap: int = Form(64),
) -> Document:
    """Upload a file (PDF, DOCX, PPTX, CSV, TXT, MD) and enqueue background ingestion."""
    filename = file.filename or "unnamed_file"
    extension = pathlib.Path(filename).suffix.lower()

    # 1. Format validation
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file format '{extension}'. Supported types are: {', '.join(SUPPORTED_EXTENSIONS)}",
            code="unsupported_format",
        )

    # 2. Read content and validate file size
    file_content = await file.read()
    file_size = len(file_content)
    if file_size > MAX_FILE_SIZE:
        raise ValidationError(
            f"File size exceeds limit of 50MB. Uploaded: {file_size / (1024 * 1024):.2f}MB",
            code="payload_too_large",
        )

    # 3. Store file binary using storage service
    storage = get_storage_backend()
    # Generate unique folder key using user_id to prevent collision
    storage_key = f"{current_user.id}/{uuid.uuid4()}{extension}"
    storage_path = await storage.upload(file_content, storage_key)

    # 4. Save initial document metadata record in DB
    doc_data = {
        "user_id": current_user.id,
        "filename": filename,
        "file_type": extension,
        "storage_path": storage_path,
        "file_size": file_size,
        "status": "pending",
    }
    doc = await doc_repo.create(doc_data)
    await doc_repo.session.commit()

    # 5. Dispatch background parser task to Celery (with synchronous fallback)
    try:
        process_document_task.delay(
            str(doc.id),
            chunk_strategy="recursive_character",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    except Exception:
        # Celery not running — process synchronously as fallback
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("Celery unavailable, processing document %s synchronously", doc.id)
        from app.workers.tasks import run_async
        from app.workers.tasks import async_process_document
        try:
            run_async(
                async_process_document(
                    document_id_str=str(doc.id),
                    chunk_strategy="recursive_character",
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
            )
        except Exception as exc:
            logger.error("Synchronous processing failed for %s: %s", doc.id, exc)

    return doc


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Rename a document",
)
async def rename_document(
    document_id: uuid.UUID,
    doc_repo: DocRepoDep,
    current_user: CurrentUserDep,
    body: dict,
) -> Document:
    """Rename a document's filename."""
    doc = await doc_repo.get_by_id_and_user(document_id, current_user.id)
    if not doc:
        raise NotFoundError("Document not found.")

    new_name = body.get("filename")
    if not new_name or not isinstance(new_name, str):
        raise ValidationError("filename is required.", code="validation_error")

    doc.filename = new_name
    doc_repo.session.add(doc)
    await doc_repo.session.commit()
    return doc


@router.get(
    "",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all uploaded documents",
)
async def list_documents(
    doc_repo: DocRepoDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> dict:
    """Retrieve paginated list of documents owned by current authenticated user."""
    items, total = await doc_repo.get_multi_by_user(current_user.id, skip=skip, limit=limit)
    page = (skip // limit) + 1 if limit else 1
    return {"items": items, "total": total, "page": page, "page_size": limit, "total_pages": max(1, -(-total // limit)) if limit else 1}


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document details",
)
async def get_document(
    document_id: uuid.UUID,
    doc_repo: DocRepoDep,
    current_user: CurrentUserDep,
) -> Document:
    """Retrieve details for a single document owned by the user."""
    doc = await doc_repo.get_by_id_and_user(document_id, current_user.id)
    if not doc:
        raise NotFoundError("Document not found.")
    return doc


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document ingestion status",
)
async def get_document_status(
    document_id: uuid.UUID,
    doc_repo: DocRepoDep,
    current_user: CurrentUserDep,
) -> dict:
    """Retrieve current processing status (pending, processing, completed, failed)."""
    doc = await doc_repo.get_by_id_and_user(document_id, current_user.id)
    if not doc:
        raise NotFoundError("Document not found.")

    progress_map = {"pending": 0.0, "processing": 50.0, "completed": 100.0, "failed": 100.0}
    progress = progress_map.get(doc.status, 0.0)

    return {
        "id": doc.id,
        "status": doc.status,
        "progress_pct": progress,
        "error_message": doc.error_message,
    }


@router.get(
    "/{document_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download document file",
)
async def download_document(
    document_id: uuid.UUID,
    doc_repo: DocRepoDep,
    current_user: CurrentUserDep,
) -> Response:
    """Download the original file for a document."""
    doc = await doc_repo.get_by_id_and_user(document_id, current_user.id)
    if not doc:
        raise NotFoundError("Document not found.")

    storage = get_storage_backend()
    file_content = await storage.download(doc.storage_path)

    media_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }
    media_type = media_types.get(doc.file_type, "application/octet-stream")

    return StreamingResponse(
        io.BytesIO(file_content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: uuid.UUID,
    doc_repo: DocRepoDep,
    current_user: CurrentUserDep,
) -> Response:
    """Remove a document record, its split chunks, and delete it from storage."""
    doc = await doc_repo.get_by_id_and_user(document_id, current_user.id)
    if not doc:
        raise NotFoundError("Document not found.")

    # 1. Delete binary from storage
    storage = get_storage_backend()
    try:
        await storage.delete(doc.storage_path)
    except Exception:
        # log warning but continue deleting DB records
        pass

    # 1.1 Delete vector embeddings from Qdrant vector store
    from app.services.rag.vector_store import QdrantAdapter
    from app.services.rag.bm25_manager import BM25IndexManager
    from app.db.redis import redis_client
    
    vector_store = QdrantAdapter()
    try:
        await vector_store.delete_by_document("document_chunks", document_id, current_user.id)
        await BM25IndexManager(redis_client).invalidate(current_user.id)
    except Exception:
        # log warning but continue deleting
        pass

    # 2. Delete database record (cascades automatically to document_chunks table)
    await doc_repo.delete_by_user(document_id, current_user.id)
    await doc_repo.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

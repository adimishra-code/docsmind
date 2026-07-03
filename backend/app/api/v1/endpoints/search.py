from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

import app.db.session as db_session
from app.api.deps import CurrentUserDep
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.models.document import Document
from app.schemas.search import SearchResponse, SearchResultItem
from app.services.rag.retriever import HybridRetriever

router = APIRouter()
logger = get_logger(__name__)

MAX_RESULTS = 50


@router.get(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Hybrid (dense + sparse + rerank) search across the user's documents",
)
async def search_documents(
    current_user: CurrentUserDep,
    q: str,
    limit: int = 10,
) -> SearchResponse:
    """Run the real hybrid retrieval pipeline and return matching document passages.

    This is the same retriever that powers RAG chat — there is no mock data here.
    """
    query = q.strip()
    if not query:
        raise ValidationError("Search query must not be empty.", code="validation_error")

    limit = max(1, min(limit, MAX_RESULTS))

    retriever = HybridRetriever()
    chunks = await retriever.retrieve(query, current_user.id, limit=limit)

    # Batch-resolve document filenames for the matched chunks.
    doc_ids = {uuid.UUID(c["payload"]["document_id"]) for c in chunks if c.get("payload", {}).get("document_id")}
    names: dict[uuid.UUID, str] = {}
    if doc_ids:
        async with db_session.AsyncSessionLocal() as session:
            rows = await session.execute(
                select(Document.id, Document.filename).where(Document.id.in_(doc_ids))
            )
            names = {d_id: fname for d_id, fname in rows.all()}

    results: list[SearchResultItem] = []
    for chunk in chunks:
        payload = chunk.get("payload", {})
        document_id = payload.get("document_id")
        if not document_id:
            continue
        excerpt = (payload.get("original_content") or payload.get("content") or "").strip()
        results.append(
            SearchResultItem(
                chunk_id=str(chunk["chunk_id"]),
                document_id=str(document_id),
                document_name=names.get(uuid.UUID(document_id), "Unknown Document"),
                page_number=payload.get("page_number"),
                score=round(float(chunk.get("rerank_score") or chunk.get("score") or 0.0), 4),
                excerpt=excerpt[:500],
            )
        )

    return SearchResponse(query=query, total=len(results), results=results)

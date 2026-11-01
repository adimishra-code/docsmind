"""Document knowledge intelligence — real, on-demand AI insights and related
documents, built on the existing LLM provider and vector store.

Nothing here is fabricated: insights are generated from the document's own text
and related documents come from real embedding similarity. Every call degrades
gracefully (empty result, never a crash) so a slow/absent local model can't take
down the viewer.
"""
from __future__ import annotations

import re
import uuid

from sqlalchemy import select

import app.db.session as db_session
from app.core.logging import get_logger
from app.models.document import Document, DocumentChunk

logger = get_logger(__name__)

# Cap the text we feed the model so a large document stays within a small local
# model's context window.
MAX_INSIGHT_CHARS = 6000
MAX_EMBED_CHARS = 2000

INSIGHTS_PROMPT = (
    "You are analyzing a document. Using ONLY the text below, produce exactly these "
    "three labelled lines and nothing else:\n"
    "Summary: a factual 2-3 sentence summary of what the document is about.\n"
    "Topics: 3 to 6 short topic phrases, comma-separated.\n"
    "Entities: up to 8 named entities (people, places, organizations, dates) that "
    "actually appear, comma-separated; write 'none' if there are no clear entities.\n\n"
    "Do not invent anything that is not in the text.\n\n"
    "Text:\n{text}"
)


def _extract_label(label: str, raw: str) -> str:
    """Pull the value after ``Label:`` up to the next label or end of text."""
    pattern = rf"{label}\s*:\s*(.*?)(?=\n\s*(?:Summary|Topics|Entities)\s*:|\Z)"
    m = re.search(pattern, raw, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _split_list(value: str) -> list[str]:
    items = [re.sub(r"^[\-\*\d.\)\s]+", "", part).strip() for part in re.split(r"[,;\n]", value)]
    out: list[str] = []
    seen: set[str] = set()
    for it in items:
        low = it.lower()
        if not it or low in {"none", "n/a", "na"} or low in seen:
            continue
        seen.add(low)
        out.append(it)
    return out[:8]


def parse_insights(raw: str) -> dict:
    """Parse the labelled LLM output into structured insight fields.

    Robust to small local models: label-based, not JSON. Returns empty fields
    (not an error) when a section is missing.
    """
    summary = " ".join(_extract_label("Summary", raw).split()).strip()
    topics = _split_list(_extract_label("Topics", raw))
    entities = _split_list(_extract_label("Entities", raw))
    return {"summary": summary or None, "topics": topics, "entities": entities}


async def _representative_text(document_id: uuid.UUID, *, limit_chars: int) -> str:
    """Concatenate a document's leading chunks as a stand-in for its full text."""
    async with db_session.AsyncSessionLocal() as session:
        stmt = (
            select(DocumentChunk.content)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .limit(12)
        )
        rows = (await session.execute(stmt)).scalars().all()
    return "\n\n".join(rows)[:limit_chars]


async def generate_insights(document_id: uuid.UUID) -> dict:
    """Generate summary/topics/entities for a document from its own text.

    Returns ``{"generated": False, ...}`` (never raises) when there is no text or
    the model call fails, so callers can honestly hide the section.
    """
    from app.services.rag.llm_provider import get_llm_provider

    text = await _representative_text(document_id, limit_chars=MAX_INSIGHT_CHARS)
    if not text.strip():
        return {"summary": None, "topics": [], "entities": [], "generated": False}

    try:
        raw = await get_llm_provider().ainvoke(INSIGHTS_PROMPT.format(text=text), temperature=0.1)
        data = parse_insights(raw)
        # Only mark generated when we actually got a usable summary.
        data["generated"] = bool(data.get("summary"))
        return data
    except Exception as exc:
        logger.warning("Insight generation failed", document_id=str(document_id), error=str(exc))
        return {"summary": None, "topics": [], "entities": [], "generated": False}


async def find_related_documents(
    user_id: uuid.UUID,
    document_id: uuid.UUID,
    *,
    limit: int = 5,
) -> list[dict]:
    """Find semantically similar documents via embedding similarity in Qdrant.

    Embeds a representative slice of the source document, searches the user's
    whole indexed corpus, drops the source document, and aggregates the best
    per-document similarity. Returns [] on any failure or when nothing indexed.
    """
    from app.services.rag.embeddings import get_embedding_provider
    from app.services.rag.vector_store import QdrantAdapter

    text = await _representative_text(document_id, limit_chars=MAX_EMBED_CHARS)
    if not text.strip():
        return []

    try:
        vector = await get_embedding_provider().embed_query(text)
        hits = await QdrantAdapter().search_chunks("document_chunks", vector, user_id, limit=40)
    except Exception as exc:
        logger.warning("Related-document search failed", document_id=str(document_id), error=str(exc))
        return []

    best: dict[str, float] = {}
    for hit in hits:
        did = (hit.get("payload") or {}).get("document_id")
        if not did or did == str(document_id):
            continue
        best[did] = max(best.get(did, 0.0), float(hit.get("score") or 0.0))

    if not best:
        return []

    top = sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    ids = [uuid.UUID(d) for d, _ in top]

    async with db_session.AsyncSessionLocal() as session:
        stmt = select(Document.id, Document.filename, Document.file_type).where(
            Document.id.in_(ids), Document.user_id == user_id
        )
        rows = {str(r.id): r for r in (await session.execute(stmt)).all()}

    related: list[dict] = []
    for did, score in top:
        row = rows.get(did)
        if row is not None:
            related.append({
                "document_id": did,
                "filename": row.filename,
                "file_type": row.file_type,
                "similarity": round(score, 4),
            })
    return related

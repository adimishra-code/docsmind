import asyncio
import time
import uuid

from sqlalchemy import select

import app.db.session as db_session
from app.core.logging import get_logger
from app.models.document import Document
from app.services.agents.state import AgentState
from app.services.rag.retriever import HybridRetriever

logger = get_logger(__name__)

# Chunks fetched per sub-question, and the ceiling on the merged context after
# de-duplication + document balancing. Kept modest so the packed context stays
# within a small local model's window while still spanning several documents.
PER_TASK_LIMIT = 5
SINGLE_TASK_LIMIT = 8
MAX_CONTEXT_CHUNKS = 16


async def _attach_document_names(chunks: list[dict]) -> None:
    """Resolve each chunk's document_id → filename (one batched query) and inject
    it into the payload. Done here — before the reasoner builds its grounded
    prompt — so the model can tell documents apart, synthesize across them, and
    cite them by name (previously every chunk read as 'Unknown File')."""
    if not chunks:
        return
    doc_ids = {uuid.UUID(c["payload"]["document_id"]) for c in chunks if c.get("payload", {}).get("document_id")}
    if not doc_ids:
        return
    async with db_session.AsyncSessionLocal() as session:
        stmt = select(Document.id, Document.filename).where(Document.id.in_(doc_ids))
        names = {d_id: fname for d_id, fname in (await session.execute(stmt)).all()}
    for chunk in chunks:
        did = chunk.get("payload", {}).get("document_id")
        if did:
            chunk["payload"]["filename"] = names.get(uuid.UUID(did), "Unknown Document")


async def retriever_node(state: AgentState) -> dict:
    """
    Retrieve grounding context for the question(s).

    For a multi-part prompt the planner produced several sub-questions; we run a
    hybrid retrieval for EACH one concurrently (so N tasks cost roughly the
    wall-clock of one) and merge the results with de-duplication + document
    balancing. Searches the whole workspace unless the user pinned a subset.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"retrieved_chunks": []}

    last_message = str(messages[-1].content)
    user_id = uuid.UUID(state["user_id"])

    document_ids_str = state.get("document_ids", [])
    document_ids = [uuid.UUID(d) for d in document_ids_str] if document_ids_str else None

    sub_questions = [q for q in (state.get("sub_questions") or []) if q.strip()] or [last_message]

    retriever = HybridRetriever()
    started = time.perf_counter()

    if len(sub_questions) == 1:
        chunks = await retriever.retrieve(
            query=sub_questions[0],
            user_id=user_id,
            limit=SINGLE_TASK_LIMIT,
            document_ids=document_ids,
            multi_query=True,
            expand_context=True,
        )
    else:
        # Independent, concurrent retrieval per sub-question, then merge/balance.
        runs = await asyncio.gather(
            *[
                retriever.retrieve(
                    query=q,
                    user_id=user_id,
                    limit=PER_TASK_LIMIT,
                    document_ids=document_ids,
                    multi_query=True,
                    expand_context=True,
                )
                for q in sub_questions
            ]
        )
        total_limit = min(len(sub_questions) * PER_TASK_LIMIT, MAX_CONTEXT_CHUNKS)
        chunks = HybridRetriever.merge_runs(runs, total_limit)

    await _attach_document_names(chunks)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "Retrieval complete",
        tasks=len(sub_questions),
        chunks=len(chunks),
        documents=len({c.get("payload", {}).get("document_id") for c in chunks}),
        retrieval_ms=elapsed_ms,
    )

    return {"retrieved_chunks": chunks}

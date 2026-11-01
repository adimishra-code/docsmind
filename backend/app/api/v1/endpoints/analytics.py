from __future__ import annotations

import collections
import re
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DBDep
from app.models.chat import ChatMessage, ChatSession
from app.models.document import Document
from app.models.usage import UsageLog

router = APIRouter()


@router.get(
    "/summary",
    status_code=status.HTTP_200_OK,
    summary="Get user platform usage and RAG analytics summary",
)
async def get_analytics_summary(
    db: DBDep,
    current_user: CurrentUserDep,
) -> dict:
    """Retrieve operational metrics including latencies, costs, token consumption, and common keywords."""
    
    # 1. Fetch latency and cost aggregates
    stmt = (
        select(
            func.avg(UsageLog.latency_ms).label("avg_latency"),
            func.sum(UsageLog.token_count).label("total_tokens"),
            func.sum(UsageLog.cost).label("total_cost"),
            func.count(UsageLog.id).label("total_requests"),
        )
        .where(UsageLog.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    aggregates = result.first()

    avg_latency = float(aggregates.avg_latency) if aggregates and aggregates.avg_latency else 0.0
    total_tokens = int(aggregates.total_tokens) if aggregates and aggregates.total_tokens else 0
    total_cost = float(aggregates.total_cost) if aggregates and aggregates.total_cost else 0.0
    total_requests = int(aggregates.total_requests) if aggregates and aggregates.total_requests else 0

    # 2. Extract most searched keywords from user's chat messages (LLM-grounded word frequency)
    message_stmt = (
        select(ChatMessage.content)
        .join(ChatSession)
        .where(ChatSession.user_id == current_user.id, ChatMessage.role == "user")
        .limit(100)
    )
    msg_result = await db.execute(message_stmt)
    user_queries = msg_result.scalars().all()

    stopwords = {
        "what", "how", "why", "who", "where", "when", "which", "whose", "whom",
        "about", "above", "after", "again", "against", "all", "are", "were",
        "was", "been", "being", "have", "has", "had", "does", "doesnt", "would",
        "should", "could", "there", "their", "these", "those", "other", "another",
        "document", "search", "find", "explain", "please", "summary", "summarize",
    }

    word_counts: collections.Counter[str] = collections.Counter()
    for query in user_queries:
        words = re.findall(r"\b[a-zA-Z]{5,15}\b", query.lower())
        filtered = [w for w in words if w not in stopwords]
        word_counts.update(filtered)

    top_topics = [
        {"topic": topic, "count": count}
        for topic, count in word_counts.most_common(5)
    ]

    # 3. Fetch detailed latency breakdowns by action
    breakdown_stmt = (
        select(UsageLog.action, func.avg(UsageLog.latency_ms).label("avg_action_latency"))
        .where(UsageLog.user_id == current_user.id)
        .group_by(UsageLog.action)
    )
    breakdown_res = await db.execute(breakdown_stmt)
    latencies = {
        row.action: round(float(row.avg_action_latency), 2)
        for row in breakdown_res.all()
    }

    return {
        "user_id": current_user.id,
        "total_requests": total_requests,
        "average_latency_ms": round(avg_latency, 2),
        "total_tokens_consumed": total_tokens,
        "cumulative_cost_usd": round(total_cost, 6),
        "latencies_breakdown": latencies,
        "most_searched_topics": top_topics,
    }


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Real-time workspace / knowledge-base status",
)
async def get_workspace_health(
    db: DBDep,
    current_user: CurrentUserDep,
) -> dict:
    """Return a live, real (never estimated) snapshot of the user's workspace:
    document counts by ingestion state, chat session count, a derived
    knowledge-base health signal, and the most recent processing activity."""
    # 1. Document counts grouped by ingestion status (single query).
    status_rows = (
        await db.execute(
            select(Document.status, func.count(Document.id))
            .where(Document.user_id == current_user.id)
            .group_by(Document.status)
        )
    ).all()
    counts = {row[0]: int(row[1]) for row in status_rows}
    total_documents = sum(counts.values())
    indexed = counts.get("completed", 0)
    failed = counts.get("failed", 0)
    # Everything not terminal (pending/processing/parsing/embedding/...) is in-flight.
    processing = total_documents - indexed - failed

    # 2. Chat session count.
    chat_sessions = int(
        (await db.execute(
            select(func.count(ChatSession.id)).where(ChatSession.user_id == current_user.id)
        )).scalar_one()
    )

    # 3. Most recent documents (latest processing activity).
    recent_rows = (
        await db.execute(
            select(Document.id, Document.filename, Document.status, Document.updated_at)
            .where(Document.user_id == current_user.id)
            .order_by(Document.updated_at.desc())
            .limit(5)
        )
    ).all()
    recent_activity = [
        {
            "id": str(row.id),
            "filename": row.filename,
            "status": row.status,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in recent_rows
    ]

    # 4. Derive a health signal purely from the real counts.
    if failed > 0:
        health = "attention"
    elif processing > 0:
        health = "processing"
    else:
        health = "healthy"

    return {
        "total_documents": total_documents,
        "indexed_documents": indexed,
        "processing_documents": processing,
        "failed_documents": failed,
        "chat_sessions": chat_sessions,
        "knowledge_base_health": health,
        "recent_activity": recent_activity,
    }

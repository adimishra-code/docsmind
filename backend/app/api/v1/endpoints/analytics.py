from __future__ import annotations

import collections
import re
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select

from app.api.deps import CurrentUserDep, DBDep
from app.models.chat import ChatMessage, ChatSession
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

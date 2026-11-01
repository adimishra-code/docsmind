import json
import uuid
from datetime import datetime, UTC

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END

from app.core.logging import get_logger
from app.services.agents.state import AgentState
from app.services.agents.nodes.planner import planner_node
from app.services.agents.nodes.retriever import retriever_node
from app.services.agents.nodes.reasoner import reasoner_node
from app.services.agents.nodes.verifier import verifier_node
from app.services.agents.nodes.critic import critic_node
from app.services.agents.nodes.composer import composer_node
from app.services.agents.nodes.chitchat import chitchat_node

logger = get_logger(__name__)

# Maximum number of critic -> reasoner revision cycles before we accept the
# current draft and move on. Prevents an unbounded loop (and runaway LLM cost /
# LangGraph GraphRecursionError) when confidence never reaches the threshold.
MAX_REVISIONS = 2


def route_verification(state: AgentState) -> str:
    confidence = state.get("confidence", 1.0)
    revisions = state.get("revision_count", 0)
    if confidence < 0.7 and revisions < MAX_REVISIONS:
        return "critic"
    return "composer"


def route_intent(state: AgentState) -> str:
    """Greetings / small talk skip retrieval and go straight to a conversational
    reply; everything else runs the full RAG pipeline."""
    if state.get("intent") == "greeting":
        return "chitchat"
    return "retriever"


def build_agent_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("reasoner", reasoner_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("composer", composer_node)
    workflow.add_node("chitchat", chitchat_node)

    workflow.set_entry_point("planner")
    workflow.add_conditional_edges(
        "planner",
        route_intent,
        {"chitchat": "chitchat", "retriever": "retriever"},
    )
    workflow.add_edge("chitchat", END)
    workflow.add_edge("retriever", "reasoner")
    workflow.add_edge("reasoner", "verifier")

    workflow.add_conditional_edges(
        "verifier",
        route_verification,
        {"critic": "critic", "composer": "composer"}
    )

    workflow.add_edge("critic", "reasoner")
    workflow.add_edge("composer", END)

    return workflow.compile(checkpointer=MemorySaver())


async def persist_graph_state(final_state: dict, thread_id: str) -> None:
    """Persist the final graph state to the database."""
    import app.db.session as db_session
    from app.models.checkpoint import GraphCheckpoint
    from sqlalchemy import select

    async with db_session.AsyncSessionLocal() as session:
        stmt = select(GraphCheckpoint).where(
            GraphCheckpoint.thread_id == thread_id
        ).order_by(GraphCheckpoint.created_at.desc()).limit(1)
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing:
            existing.state_json = json.dumps(final_state, default=str)
            existing.status = "completed"
            existing.completed_at = datetime.now(UTC)
        else:
            parts = thread_id.split(":")
            u_id = uuid.UUID(parts[0]) if len(parts) >= 2 else uuid.UUID(final_state.get("user_id", "00000000-0000-0000-0000-000000000000"))
            s_id = uuid.UUID(parts[1]) if len(parts) >= 2 else uuid.UUID(final_state.get("session_id", "00000000-0000-0000-0000-000000000000"))

            checkpoint = GraphCheckpoint(
                thread_id=thread_id,
                user_id=u_id,
                session_id=s_id,
                state_json=json.dumps(final_state, default=str),
                status="completed",
                completed_at=datetime.now(UTC),
            )
            session.add(checkpoint)
        await session.commit()

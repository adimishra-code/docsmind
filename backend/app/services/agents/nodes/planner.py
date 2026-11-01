from app.core.logging import get_logger
from app.services.agents.decompose import (
    DECOMPOSE_PROMPT,
    looks_multipart,
    parse_subquestions,
)
from app.services.agents.state import AgentState
from app.services.rag.llm_provider import get_llm_provider

logger = get_logger(__name__)


async def planner_node(state: AgentState) -> dict:
    """
    Decompose the user's request into independent sub-questions so retrieval can
    run once per topic instead of blending everything into a single weak query.

    Cost-aware: greetings and simple single questions make NO LLM call here (the
    old planner issued an unused "execution plan" call on every message — pure
    latency). The decomposer runs only when a cheap heuristic sees multiple asks.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"plan": "No messages to process.", "sub_questions": []}

    # Small talk is routed straight to the conversational path — no planning.
    if state.get("intent") == "greeting":
        return {"plan": "Greeting — respond conversationally without retrieval.", "sub_questions": []}

    last_message = messages[-1].content

    if not looks_multipart(last_message):
        # Single focused question — retrieve for it directly, no LLM call.
        return {"plan": "Single-topic question.", "sub_questions": [last_message.strip()]}

    try:
        raw = await get_llm_provider().ainvoke(
            DECOMPOSE_PROMPT.format(text=last_message), temperature=0.0
        )
        sub_questions = parse_subquestions(raw, last_message)
    except Exception as exc:
        # Decomposition is an optimization, never a hard dependency — fall back
        # to treating the whole prompt as one query.
        logger.warning("Question decomposition failed; using the whole prompt", error=str(exc))
        sub_questions = [last_message.strip()]

    logger.info("Planner decomposed request", tasks=len(sub_questions))
    return {
        "plan": f"Decomposed into {len(sub_questions)} sub-question(s).",
        "sub_questions": sub_questions,
    }

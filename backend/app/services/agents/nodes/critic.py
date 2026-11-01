from app.services.agents.state import AgentState
from app.services.rag.llm_provider import get_llm_provider

async def critic_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    query = messages[-1].content if messages else ""
    draft = state.get("final_response", "")
    citations = state.get("citations", [])
    confidence = state.get("confidence", 0.0)
    next_revision = state.get("revision_count", 0) + 1

    if not draft:
        return {
            "verification_feedback": "No draft was generated. Please retrieve relevant context and try again.",
            "revision_count": next_revision,
        }

    prompt = (
        f"You are a critique agent evaluating a draft response for an enterprise document Q&A system.\n\n"
        f"Original Query: {query}\n\n"
        f"Draft Response: {draft}\n\n"
        f"Citations Found: {len(citations)}\n"
        f"Confidence Score: {confidence}\n\n"
        f"Analyze the draft and provide 2-3 specific, actionable sentences of feedback covering:\n"
        f"1. Claims that appear unsupported by the context (hallucinations)\n"
        f"2. Where citations are missing or incorrect\n"
        f"3. What specific improvements the reasoner should make in its next attempt\n\n"
        f"Critique:"
    )

    provider = get_llm_provider()
    feedback = await provider.ainvoke(prompt, temperature=0.3)
    return {"verification_feedback": feedback, "revision_count": next_revision}

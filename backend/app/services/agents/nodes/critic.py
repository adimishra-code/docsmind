from app.services.agents.state import AgentState

async def critic_node(state: AgentState) -> dict:
    """
    Evaluates the draft. If confidence is low, provides feedback to the reasoner.
    (This is a placeholder node that demonstrates reflection).
    """
    confidence = state.get("confidence", 1.0)
    
    if confidence < 0.7:
        feedback = "The response lacks sufficient citations from the retrieved context. Please retry and ensure claims are grounded."
    else:
        feedback = "Response is solid."
        
    return {"verification_feedback": feedback}

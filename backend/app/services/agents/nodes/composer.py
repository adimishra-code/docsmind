from app.services.agents.state import AgentState

async def composer_node(state: AgentState) -> dict:
    """
    In a streaming setup, the composer doesn't need to do much if the reasoner/verifier 
    already built the final text. 
    It just finalizes the state.
    """
    return {}

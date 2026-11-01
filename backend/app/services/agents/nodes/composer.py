from app.services.agents.state import AgentState


async def composer_node(state: AgentState) -> dict:
    """Finalize the answer.

    The reasoner now streams its grounded answer directly to the client
    token-by-token, and the verifier attaches citations without altering the
    text. To keep what the user watched being typed identical to what we persist
    and reload, the composer no longer rewrites the answer — it passes the
    verified draft through unchanged. (The UI renders the authoritative Sources
    list from the citation objects, so no textual Sources section is added.)
    """
    final_response = state.get("final_response", "")
    if not final_response:
        return {"final_response": "I could not generate a response based on the available documents."}
    return {"final_response": final_response}

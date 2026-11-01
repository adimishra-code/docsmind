from app.services.agents.state import AgentState
from app.services.rag.llm_provider import get_llm_provider

# Kept short and warm — this path handles greetings / small talk only, so there
# is no retrieval, no citations, and no "based on the documents" framing.
SYSTEM = (
    "You are DocsMind, a friendly enterprise document assistant. "
    "The user sent a greeting or a short piece of small talk. "
    "Reply naturally and briefly (one or two sentences), in a warm, professional tone. "
    "Do not mention documents, sources, or retrieval unless the user asks. "
    "Do not apologize. Do not add any preamble like 'Here is'. "
    "If it fits, gently invite them to ask a question about their documents."
)


async def chitchat_node(state: AgentState) -> dict:
    """Answer greetings / small talk conversationally, bypassing RAG entirely."""
    messages = state.get("messages", [])
    user_message = messages[-1].content if messages else "Hi"

    prompt = f"{SYSTEM}\n\nUser: {user_message}\nAssistant:"

    # Stream so the greeting is emitted token-by-token to the client, exactly
    # like a grounded answer (the ChatService forwards these live).
    provider = get_llm_provider()
    tokens: list[str] = []
    async for token in provider.astream(prompt, temperature=0.3):
        tokens.append(token)
    reply = "".join(tokens).strip()

    return {
        "final_response": reply or "Hi! How can I help you with your documents today?",
        "citations": [],
        "confidence": 1.0,
    }

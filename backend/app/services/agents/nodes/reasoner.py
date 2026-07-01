from app.services.agents.state import AgentState
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.services.rag.prompt_guard import PromptGuard

async def reasoner_node(state: AgentState) -> dict:
    chunks = state.get("retrieved_chunks", [])
    messages = state.get("messages", [])

    if not messages:
        return {}

    user_query = messages[-1].content
    feedback = state.get("verification_feedback", "")

    system_prompt = PromptGuard.build_grounded_system_prompt(chunks)

    if feedback:
        system_prompt += (
            f"\n\n--- Previous Critique to address ---\n"
            f"{feedback}\n"
            f"--- End Critique ---\n\n"
            f"Revise your response to address each point above."
        )

    kwargs = {"model": settings.LLM_MODEL, "api_key": settings.OPENAI_API_KEY, "temperature": 0.0}
    if settings.LLM_BASE_URL:
        kwargs["base_url"] = settings.LLM_BASE_URL
    llm = ChatOpenAI(**kwargs)

    prompt = f"{system_prompt}\n\nUser Query: {user_query}\n\nDraft a comprehensive response based ONLY on the evidence above."

    tokens = []
    async for chunk in llm.astream(prompt):
        if chunk.content:
            tokens.append(chunk.content)

    return {"final_response": "".join(tokens)}

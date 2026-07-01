from app.services.agents.state import AgentState
from langchain_openai import ChatOpenAI
from app.core.config import settings

async def planner_node(state: AgentState) -> dict:
    """
    Analyzes the user's latest message and decides if retrieval is needed,
    what tools to use, and outlines a high-level strategy.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"plan": "No messages to process."}

    # In a full implementation, we'd invoke the LLM to generate a JSON plan.
    # For now, we simulate the planner's output.
    last_message = messages[-1].content
    
    kwargs = {"model": settings.LLM_MODEL, "api_key": settings.OPENAI_API_KEY}
    if settings.LLM_BASE_URL:
        kwargs["base_url"] = settings.LLM_BASE_URL
    llm = ChatOpenAI(**kwargs)
    
    prompt = f"""
    You are the Planner Agent. Analyze this user request and output a brief execution plan.
    Determine if document retrieval is necessary.
    User Request: {last_message}
    """
    
    response = await llm.ainvoke(prompt)
    
    return {"plan": response.content}

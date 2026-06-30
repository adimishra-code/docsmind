from app.services.agents.state import AgentState
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.services.rag.prompt_guard import PromptGuard

async def reasoner_node(state: AgentState) -> dict:
    """
    Synthesizes the retrieved information into a structured reasoning chain.
    """
    chunks = state.get("retrieved_chunks", [])
    messages = state.get("messages", [])
    
    if not messages:
        return {}

    user_query = messages[-1].content
    system_prompt = PromptGuard.build_grounded_system_prompt(chunks)
    
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY, temperature=0.0)
    
    # We ask the LLM to output its raw reasoning as a draft string
    prompt = f"{system_prompt}\n\nUser Query: {user_query}\n\nDraft a comprehensive response based ONLY on the evidence above."
    
    response = await llm.ainvoke(prompt)
    
    return {"final_response": response.content} # We store it in final_response temporarily for the verifier to check

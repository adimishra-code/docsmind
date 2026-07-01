from app.services.agents.state import AgentState
from langchain_openai import ChatOpenAI
from app.core.config import settings

async def composer_node(state: AgentState) -> dict:
    final_response = state.get("final_response", "")
    citations = state.get("citations", [])
    query = state.get("messages", [])[-1].content if state.get("messages") else ""

    if not final_response:
        return {"final_response": "I could not generate a response based on the available documents."}

    if not citations:
        return {"final_response": final_response}

    kwargs = {"model": settings.LLM_MODEL, "api_key": settings.OPENAI_API_KEY, "temperature": 0.0}
    if settings.LLM_BASE_URL:
        kwargs["base_url"] = settings.LLM_BASE_URL
    llm = ChatOpenAI(**kwargs)

    citation_lines = []
    for c in citations:
        citation_lines.append(
            f"[{c['citation_index']}] {c['document_name']}"
            f"{' (Page ' + str(c['page_number']) + ')' if c.get('page_number') else ''}"
        )
    formatted_sources = "\n".join(citation_lines)

    prompt = (
        f"Polish the following answer for readability. Keep all existing [N] citation markers intact. "
        f"Append a '---\nSources:\n{formatted_sources}' section at the end.\n"
        f"Do not change facts or add new information.\n\n"
        f"Answer:\n{final_response}"
    )

    response = await llm.ainvoke(prompt)
    return {"final_response": response.content}

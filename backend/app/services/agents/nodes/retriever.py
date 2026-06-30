import uuid
from app.services.agents.state import AgentState
from app.services.rag.retriever import HybridRetriever

async def retriever_node(state: AgentState) -> dict:
    """
    Executes the HybridRetriever based on the user's query and the plan.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"retrieved_chunks": []}
        
    last_message = messages[-1].content
    user_id = uuid.UUID(state["user_id"])
    
    document_ids_str = state.get("document_ids", [])
    document_ids = [uuid.UUID(d) for d in document_ids_str] if document_ids_str else None
    
    retriever = HybridRetriever()
    
    # Execute actual hybrid retrieval
    chunks = await retriever.retrieve(
        query=last_message,
        user_id=user_id,
        limit=5,
        document_ids=document_ids
    )
    
    return {"retrieved_chunks": chunks}

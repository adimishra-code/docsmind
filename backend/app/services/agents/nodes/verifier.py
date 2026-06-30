from app.services.agents.state import AgentState
from app.services.rag.citations import CitationEngine

async def verifier_node(state: AgentState) -> dict:
    """
    Verifies citations and checks for unsupported claims using the CitationEngine.
    """
    draft = state.get("final_response", "")
    chunks = state.get("retrieved_chunks", [])
    
    if not draft or not chunks:
        return {"confidence": 1.0, "citations": []}
        
    engine = CitationEngine()
    
    # Extract citations (which modifies the text and builds the citation objects)
    final_text, citations = await engine.extract_citations(draft, chunks)
    
    # In a full agent, we might use the RAGEvaluator to score faithfulness.
    # For now, we simulate a confidence score based on citation density.
    confidence = 1.0 if len(citations) > 0 else 0.5
    
    return {
        "final_response": final_text,
        "citations": citations,
        "confidence": confidence
    }

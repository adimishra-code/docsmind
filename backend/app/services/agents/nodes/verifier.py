from app.core.config import settings
from app.core.logging import get_logger
from app.services.agents.state import AgentState
from app.services.rag.citations import CitationEngine

logger = get_logger(__name__)


async def verifier_node(state: AgentState) -> dict:
    """
    Verifies citations and checks for unsupported claims using the CitationEngine.
    """
    draft = state.get("final_response", "")
    chunks = state.get("retrieved_chunks", [])

    if not draft or not chunks:
        return {"confidence": 1.0, "citations": []}

    engine = CitationEngine()

    # Extract citations (which extracts bracketed markers and builds the citation objects)
    final_text, citations = await engine.extract_citations(draft, chunks)

    if settings.DEBUG:
        # Citations shown to the user — compare against reasoner.final_context to
        # confirm the grounding surfaced in the UI matches the prompt context.
        logger.debug(
            "verifier.citations",
            citations=[
                {"n": c.get("citation_index"), "doc": c.get("document_name"), "page": c.get("page_number")}
                for c in citations
            ],
        )

    # High confidence if citations were extracted, or if general knowledge was intentionally invoked
    lower_draft = draft.lower()
    has_fallback = "general ai knowledge" in lower_draft or "general knowledge" in lower_draft or "not found in" in lower_draft
    confidence = 1.0 if (len(citations) > 0 or has_fallback) else 0.5

    return {
        "final_response": final_text,
        "citations": citations,
        "confidence": confidence,
    }

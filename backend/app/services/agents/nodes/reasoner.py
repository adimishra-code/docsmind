import time

from app.core.config import settings
from app.core.logging import get_logger
from app.services.agents.state import AgentState
from app.services.rag.llm_provider import get_llm_provider
from app.services.rag.prompt_guard import PromptGuard

logger = get_logger(__name__)

# Base answering rules, shared by single- and multi-part questions.
_BASE_RULES = (
    "Answer using the context above whenever relevant.\n"
    "- If the context contains the answer, ground your response in the excerpts and cite each claim with bracketed source numbers, e.g. [1] or [2][3].\n"
    "- If the context does NOT contain the answer, explicitly state:\n"
    "  > ℹ️ *Not found in your uploaded documents. Answering from general AI knowledge:*\n\n"
    "  and answer the user's question clearly and helpfully using your own general knowledge (without citation brackets).\n"
    "- Begin directly with the answer. No unnecessary preamble ('Here is', 'Based on the evidence') "
    "and no trailing Sources section."
)


def _single_prompt(system_prompt: str, query: str) -> str:
    return (
        f"{system_prompt}\n\n{_BASE_RULES}\n\n"
        f"Question: {query}"
    )


def _multipart_prompt(system_prompt: str, query: str, sub_questions: list[str]) -> str:
    headings = "\n".join(f"## {q}" for q in sub_questions)
    return (
        f"{system_prompt}\n\n{_BASE_RULES}\n\n"
        f"The user's request has several parts. Answer EACH part under its own Markdown "
        f"heading, in this exact order and wording:\n\n{headings}\n\n"
        "Rules for the structured answer:\n"
        "- Answer every heading independently from the evidence, with citations.\n"
        "- If the evidence does not cover a specific heading, write under it:\n"
        "  > ℹ️ *Not found in your uploaded documents. Answering from general AI knowledge:*\n"
        "  and answer that part using your general knowledge.\n"
        "- Keep each section focused; do not repeat the same evidence across sections "
        "unless it genuinely applies to more than one.\n\n"
        f"Original request: {query}"
    )


async def reasoner_node(state: AgentState) -> dict:
    chunks = state.get("retrieved_chunks", [])
    messages = state.get("messages", [])

    if not messages:
        return {}

    user_query = messages[-1].content
    feedback = state.get("verification_feedback", "")
    sub_questions = [q for q in (state.get("sub_questions") or []) if q.strip()]

    if not chunks:
        prompt = (
            "You are DocsMind AI, an intelligent, helpful document assistant.\n\n"
            "The user asked a question, but there are no relevant documents uploaded in their workspace.\n\n"
            "Instructions:\n"
            "1. Start your response with:\n"
            "> ℹ️ *No relevant document context found. Answering from general AI knowledge:*\n\n"
            "2. Provide a clear, thorough, and helpful answer to the user's question using your own broad general knowledge.\n"
            "3. Do not include bracketed citation numbers (like [1]) since no documents were used.\n\n"
            f"Question: {user_query}"
        )
    else:
        system_prompt = PromptGuard.build_grounded_system_prompt(chunks)

        if feedback:
            system_prompt += (
                f"\n\n--- Previous Critique to address ---\n"
                f"{feedback}\n"
                f"--- End Critique ---\n\n"
                f"Revise your response to address each point above."
            )

        if len(sub_questions) > 1:
            prompt = _multipart_prompt(system_prompt, user_query, sub_questions)
        else:
            prompt = _single_prompt(system_prompt, user_query)

    if settings.DEBUG:
        # The EXACT numbered context ([1..N]) handed to the model — these indices
        # are what citation markers map back to, so this trace is the ground
        # truth for "does the final prompt match the citations".
        logger.debug(
            "reasoner.final_context",
            query=user_query,
            context=[
                {
                    "n": i + 1,
                    "doc": (c.get("payload") or {}).get("filename"),
                    "page": (c.get("payload") or {}).get("page_number"),
                    "text": ((c.get("payload") or {}).get("content") or "")[:100].replace("\n", " "),
                }
                for i, c in enumerate(chunks)
            ],
        )

    provider = get_llm_provider()
    started = time.perf_counter()
    ttft_ms: float | None = None
    tokens: list[str] = []
    async for token in provider.astream(prompt, temperature=0.0):
        if ttft_ms is None:
            ttft_ms = (time.perf_counter() - started) * 1000
        tokens.append(token)

    logger.info(
        "Reasoner generation complete",
        structured=len(sub_questions) > 1,
        chunks=len(chunks),
        ttft_ms=int(ttft_ms) if ttft_ms is not None else None,
        generation_ms=int((time.perf_counter() - started) * 1000),
    )
    return {"final_response": "".join(tokens)}

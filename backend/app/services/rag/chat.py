from __future__ import annotations

import asyncio
import json
import re
import time
from typing import AsyncGenerator, Any
import uuid

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import get_logger
import app.db.session as db_session
from app.models.chat import ChatMessage, ChatSession
from app.models.usage import UsageLog
from app.schemas.chat import MessageRole
from app.services.rag.citations import CitationEngine
from app.services.rag.retriever import HybridRetriever
from app.services.rag.prompt_guard import PromptGuard
from app.services.rag.token_manager import token_manager

logger = get_logger(__name__)


# Strip common LLM "framing" artifacts so answers read naturally.
_PREAMBLE_RE = re.compile(
    r"^\s*(?:sure|certainly|of course|absolutely)[!,.]?\s+(?=\S)"
    r"|^\s*here(?:'s| is)\s+(?:the\s+|a\s+|your\s+)?"
    r"(?:polished|revised|final|improved|updated|refined|reworded|cleaned[- ]?up|rewritten)\s+"
    r"(?:version|answer|response|text)\b[^:\n]*:?\s*",
    re.IGNORECASE,
)
# The UI renders the authoritative Sources list, so drop any model-appended
# "Sources:" block to avoid duplicated, noisy citations.
_TRAILING_SOURCES_RE = re.compile(r"\n+\s*-{0,3}\s*\n*sources?\s*:\s*\n.*$", re.IGNORECASE | re.DOTALL)


def _clean_response(text: str) -> str:
    """Remove leading preamble artifacts and any appended Sources block."""
    if not text:
        return text
    cleaned = _PREAMBLE_RE.sub("", text, count=1)
    cleaned = _TRAILING_SOURCES_RE.sub("", cleaned)
    return cleaned.strip()


# Placeholder titles a freshly-created session carries until its first real
# message; only these are auto-replaced, so a user's manual rename is never lost.
_DEFAULT_TITLES = {"", "new chat", "untitled chat", "untitled"}
_TITLE_MAX_LEN = 48

_LEAD_INS = sorted(
    [
        "can you please tell me about", "can you tell me about", "could you tell me about",
        "what can you tell me about", "what do you know about", "can you tell me", "could you tell me",
        "i would like to know about", "i'd like to know about", "i want to know about", "i want to know",
        "please tell me about", "please tell me", "do you know about", "tell me about", "talk about",
        "can you explain", "could you explain", "can you describe", "can you list", "can you summarize",
        "can you", "could you", "would you", "please", "tell me", "explain", "describe",
        "summarize", "summarise", "give me", "show me", "list", "provide",
        "what is", "what are", "what's", "whats", "who is", "who are", "who's",
        "how do i", "how do", "how does", "how to", "do you know", "help me with", "help me",
        "about", "regarding", "info on", "information about", "the", "a", "an",
    ],
    key=len,
    reverse=True,
)

_TITLE_CONNECTORS = {
    "of", "by", "in", "on", "to", "for", "a", "an", "the", "and", "or", "vs", "vs.",
    "with", "at", "as", "from", "into", "per", "but", "between", "about", "over",
    "under", "than", "nor", "off", "up", "against", "before", "after",
}


def _strip_lead_ins(text: str) -> str:
    current = text
    changed = True
    while changed and current:
        changed = False
        lowered = current.lower()
        for phrase in _LEAD_INS:
            if lowered == phrase or lowered.startswith(phrase + " "):
                current = current[len(phrase):].lstrip(" ,:;-")
                changed = True
                break
    return current


def _smart_title_case(text: str) -> str:
    words = text.split()
    out: list[str] = []
    for i, word in enumerate(words):
        if any(c.isupper() for c in word):
            out.append(word)
        elif i > 0 and word.lower() in _TITLE_CONNECTORS:
            out.append(word.lower())
        else:
            out.append(word[:1].upper() + word[1:])
    return " ".join(out)


def _derive_title(text: str) -> str:
    cleaned = " ".join((text or "").strip().split())
    if not cleaned:
        return "New Chat"
    stripped = _strip_lead_ins(cleaned).strip(" ?!.,:;-—")
    base = stripped if stripped else cleaned.rstrip(" ?!.,:;-—")
    if len(base) > _TITLE_MAX_LEN:
        base = base[:_TITLE_MAX_LEN].rsplit(" ", 1)[0] or base[:_TITLE_MAX_LEN]
        return _smart_title_case(base.rstrip(" ,.:;-—")) + "…"
    return _smart_title_case(base) or "New Chat"


def _build_meta_dict(
    *,
    confidence: float,
    chunk_count: int,
    total_ms: int,
    token_count: int,
    cached: bool = False,
) -> dict[str, Any]:
    """Build the assistant-message meta persisted to DB and returned on reload.
    Key names are camelCase to match the frontend MessageMeta interface directly."""
    return {
        "confidence": confidence,
        "chunkCount": chunk_count,
        "totalMs": total_ms,
        "latencyMs": total_ms,
        "tokenCount": token_count,
        "model": settings.LLM_MODEL,
        "provider": settings.LLM_PROVIDER,
        "cached": cached,
    }


async def _persist_turn(
    *,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    assistant_content: str,
    citations: list[dict[str, Any]],
    meta_dict: dict[str, Any],
    token_count: int,
    latency_ms: int,
    cached: bool,
) -> None:
    """Write the assistant ChatMessage and a UsageLog row in a single transaction."""
    async with db_session.AsyncSessionLocal() as db:
        db.add(ChatMessage(
            chat_id=session_id,
            role="assistant",
            content=assistant_content,
            citations=citations or None,
            meta=meta_dict,
        ))
        db.add(UsageLog(
            user_id=user_id,
            action="agent_completion_cached" if cached else "agent_completion",
            token_count=token_count,
            latency_ms=latency_ms,
            cost=0.0 if cached else 0.00015 * (token_count / 1000),
            extra_info={
                "session_id": str(session_id),
                "citations_found": len(citations),
                "confidence": meta_dict.get("confidence", 1.0),
                "cached": cached,
            },
        ))
        await db.commit()


class ChatService:
    """Manages conversational memory, retrieval grounding, and streaming LLM executions."""

    CACHE_TTL = 300  # 5 minutes

    def __init__(self) -> None:
        self.retriever = HybridRetriever()
        self.citation_engine = CitationEngine()

    async def _cache_key(self, user_id: uuid.UUID, query: str, document_ids: list[uuid.UUID] | None) -> str:
        import hashlib
        parts = [str(user_id), query]
        if document_ids:
            parts.extend(sorted(str(d) for d in document_ids))
        raw = "|".join(parts)
        return "rag:cache:{0}".format(hashlib.sha256(raw.encode()).hexdigest())

    async def _check_cache(self, key: str) -> dict | None:
        try:
            from app.db.redis import redis_client
            data = await redis_client.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    async def _set_cache(self, key: str, data: dict) -> None:
        try:
            from app.db.redis import redis_client
            await redis_client.setex(key, self.CACHE_TTL, json.dumps(data))
        except Exception:
            pass

    async def stream_chat_response(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        message_content: str,
        *,
        document_ids: list[uuid.UUID] | None = None,
        multi_query: bool = False,
        expand_context: bool = False,
    ) -> AsyncGenerator[str, None]:
        """Orchestrate the RAG stream.

        SSE event order (deterministic, identical for cache-hit and cache-miss):
            meta → [title] → [agent_state…] → [content_reset] → content → citations → stats → [DONE]

        Persistence happens AFTER [DONE] in both paths so DB writes never add
        latency between the last token and stream completion from the client's
        perspective.
        """
        from app.services.agents.graph import build_agent_graph
        from langchain_core.messages import HumanMessage

        start_time = time.perf_counter()
        sanitized_content = PromptGuard.sanitize_query(message_content)

        # ── Announce model/provider so the UI can label the response honestly ──
        yield f"data: {json.dumps({'type': 'meta', 'model': settings.LLM_MODEL, 'provider': settings.LLM_PROVIDER})}\n\n"

        # ── Step 1: persist user message + optional title derivation ──────────
        # Always runs before the cache check so both paths have identical DB state.
        new_title: str | None = None
        async with db_session.AsyncSessionLocal() as db:
            db.add(ChatMessage(
                chat_id=session_id,
                role="user",
                content=sanitized_content,
            ))
            chat = await db.get(ChatSession, session_id)
            if chat and (chat.title or "").strip().lower() in _DEFAULT_TITLES:
                new_title = _derive_title(sanitized_content)
                chat.title = new_title
            await db.commit()

        if new_title:
            yield f"data: {json.dumps({'type': 'title', 'title': new_title})}\n\n"

        # ── Step 2: cache lookup ───────────────────────────────────────────────
        cache_key = await self._cache_key(user_id, sanitized_content, document_ids)
        cached = await self._check_cache(cache_key)

        if cached:
            logger.info("RAG cache hit", key=cache_key)
            cached_response: str = cached["final_response"]
            citations: list[dict[str, Any]] = cached.get("citations") or []
            confidence: float = cached.get("confidence", 1.0)
            chunk_count: int = cached.get("chunk_count", 0)

            # Emit cached content as one event — no artificial delay.
            # The cache-hit path has no real token stream so we just surface the
            # answer immediately; any drip-feed here is pure fabrication.
            yield f"data: {json.dumps({'type': 'content', 'content': cached_response})}\n\n"

            yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"

            cached_tokens = (
                token_manager.count_tokens(cached_response)
                + token_manager.count_tokens(message_content)
            )
            cached_latency_ms = int((time.perf_counter() - start_time) * 1000)

            yield f"data: {json.dumps({'type': 'stats', 'confidence': confidence, 'chunk_count': chunk_count, 'token_count': cached_tokens, 'latency_ms': cached_latency_ms, 'cached': True})}\n\n"

            # [DONE] is yielded before DB writes so the client can commit
            # the message immediately without waiting for persistence.
            yield "data: [DONE]\n\n"

            meta_dict = _build_meta_dict(
                confidence=confidence,
                chunk_count=chunk_count,
                total_ms=cached_latency_ms,
                token_count=cached_tokens,
                cached=True,
            )
            await _persist_turn(
                session_id=session_id,
                user_id=user_id,
                assistant_content=cached_response,
                citations=citations,
                meta_dict=meta_dict,
                token_count=cached_tokens,
                latency_ms=cached_latency_ms,
                cached=True,
            )
            return

        # ── Step 3: fresh RAG execution ────────────────────────────────────────
        logger.info("RAG cache miss", key=cache_key)

        graph = build_agent_graph()
        from app.services.agents.intent import classify_intent

        initial_state = {
            "messages": [HumanMessage(content=sanitized_content)],
            "session_id": str(session_id),
            "user_id": str(user_id),
            "document_ids": [str(d) for d in document_ids] if document_ids else [],
            "intent": classify_intent(sanitized_content),
        }

        final_state: dict[str, Any] = {}
        thread_id = "{0}:{1}".format(user_id, session_id)

        node_names = {"planner", "retriever", "reasoner", "verifier", "critic", "composer", "chitchat"}
        streaming_nodes = {"reasoner", "chitchat"}
        streamed_any = False

        try:
            async for event in graph.astream_events(
                initial_state,
                config={"configurable": {"thread_id": thread_id}},
                version="v2",
            ):
                etype = event["event"]
                name = event.get("name")
                node = (event.get("metadata") or {}).get("langgraph_node")

                if etype == "on_chain_start" and name in node_names:
                    if name in streaming_nodes and streamed_any:
                        yield f"data: {json.dumps({'type': 'content_reset'})}\n\n"
                        streamed_any = False
                    yield f"data: {json.dumps({'type': 'agent_state', 'node': name, 'status': 'running'})}\n\n"

                elif etype == "on_chain_end" and name in node_names:
                    output = (event.get("data") or {}).get("output")
                    if isinstance(output, dict):
                        final_state.update(output)

                elif etype == "on_chat_model_stream" and node in streaming_nodes:
                    chunk = (event.get("data") or {}).get("chunk")
                    token = getattr(chunk, "content", "") or ""
                    if token:
                        streamed_any = True
                        yield f"data: {json.dumps({'type': 'content', 'content': token})}\n\n"

            if final_state:
                from app.services.agents.graph import persist_graph_state
                await persist_graph_state(final_state, thread_id)

            if not final_state.get("final_response") and not streamed_any:
                # Graph ran but produced no text — emit a safe fallback so the
                # client is never left with an empty bubble and infinite spinner.
                fallback_text = "I was unable to generate a response. Please try rephrasing your question."
                fallback_ms = int((time.perf_counter() - start_time) * 1000)
                fallback_tokens = (
                    token_manager.count_tokens(fallback_text)
                    + token_manager.count_tokens(message_content)
                )
                yield f"data: {json.dumps({'type': 'content', 'content': fallback_text})}\n\n"
                yield f"data: {json.dumps({'type': 'citations', 'citations': []})}\n\n"
                yield f"data: {json.dumps({'type': 'stats', 'confidence': 0.0, 'chunk_count': 0, 'token_count': fallback_tokens, 'latency_ms': fallback_ms})}\n\n"
                yield "data: [DONE]\n\n"
                # Persist the fallback so it survives reload.
                await _persist_turn(
                    session_id=session_id,
                    user_id=user_id,
                    assistant_content=fallback_text,
                    citations=[],
                    meta_dict=_build_meta_dict(
                        confidence=0.0,
                        chunk_count=0,
                        total_ms=fallback_ms,
                        token_count=fallback_tokens,
                        cached=False,
                    ),
                    token_count=fallback_tokens,
                    latency_ms=fallback_ms,
                    cached=False,
                )
                return

            if "final_response" in final_state:
                text: str = final_state["final_response"]
                if not streamed_any:
                    # No live streaming occurred (e.g. streaming disabled for this
                    # provider).  Emit the full response as one content event —
                    # no artificial drip-feed sleep.
                    text = _clean_response(text)
                    yield f"data: {json.dumps({'type': 'content', 'content': text})}\n\n"

                citations = final_state.get("citations") or []
                yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"

                total_duration_ms = int((time.perf_counter() - start_time) * 1000)
                token_count = token_manager.count_tokens(text) + token_manager.count_tokens(message_content)
                chunk_count = len(final_state.get("retrieved_chunks") or [])
                confidence = final_state.get("confidence", 1.0)

                meta_dict = _build_meta_dict(
                    confidence=confidence,
                    chunk_count=chunk_count,
                    total_ms=total_duration_ms,
                    token_count=token_count,
                    cached=False,
                )

                yield (
                    "data: "
                    + json.dumps({
                        "type": "stats",
                        "confidence": confidence,
                        "chunk_count": chunk_count,
                        "token_count": token_count,
                        "latency_ms": total_duration_ms,
                    })
                    + "\n\n"
                )

                # Yield [DONE] before DB writes so the client commits the message
                # immediately without waiting for persistence latency.
                yield "data: [DONE]\n\n"

                await _persist_turn(
                    session_id=session_id,
                    user_id=user_id,
                    assistant_content=text,
                    citations=citations,
                    meta_dict=meta_dict,
                    token_count=token_count,
                    latency_ms=total_duration_ms,
                    cached=False,
                )
                await self._set_cache(cache_key, {
                    "final_response": text,
                    "citations": citations,
                    "confidence": confidence,
                    "chunk_count": chunk_count,
                    "token_count": token_count,
                })
                return

        except Exception as exc:
            logger.exception("LangGraph execution failed")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

        # Reached only when: (a) an exception was raised, or (b) final_state has
        # no final_response key and something was streamed (edge case).
        yield "data: [DONE]\n\n"

    async def _load_conversation_history(self, session_id: uuid.UUID) -> list[tuple[str, str]]:
        """Load past messages for context, keeping memory bounded (last 8 turns)."""
        async with db_session.AsyncSessionLocal() as session:
            stmt = (
                select(ChatMessage)
                .where(ChatMessage.chat_id == session_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(8)
            )
            result = await session.execute(stmt)
            messages = list(result.scalars().all())
        messages.reverse()
        return [(m.role, m.content) for m in messages]

"""Integration test for the greeting fast-path in the agent graph.

Asserts that a greeting is routed straight to the conversational node — the
retriever/reasoner never run — and produces a reply with no citations. Uses a
fake LLM provider so it needs no DB, embeddings, or vector store.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

from langchain_core.messages import HumanMessage

from app.services.agents.graph import build_agent_graph


class _FakeProvider:
    async def ainvoke(self, prompt: str, *, temperature: float = 0.0) -> str:
        return "Hi! How can I help you with your documents today?"

    async def astream(self, prompt: str, *, temperature: float = 0.0):
        for tok in ["Hi! ", "How ", "can ", "I ", "help?"]:
            yield tok


@pytest.mark.asyncio
async def test_greeting_skips_retrieval_and_has_no_citations() -> None:
    with patch("app.services.agents.nodes.chitchat.get_llm_provider", return_value=_FakeProvider()):
        graph = build_agent_graph()
        state = {
            "messages": [HumanMessage(content="Hi")],
            "session_id": "s",
            "user_id": "u",
            "document_ids": [],
            "intent": "greeting",
        }

        visited: list[str] = []
        final: dict = {}
        async for event in graph.astream(state, config={"configurable": {"thread_id": "t"}}):
            for node, out in event.items():
                visited.append(node)
                if isinstance(out, dict):
                    final.update(out)

    # Retrieval / reasoning must be skipped entirely for small talk.
    assert "retriever" not in visited
    assert "reasoner" not in visited
    assert "chitchat" in visited
    # A real conversational reply, with no citations.
    assert final.get("final_response")
    assert final.get("citations", []) == []

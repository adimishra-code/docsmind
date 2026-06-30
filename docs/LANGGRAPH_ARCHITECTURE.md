# LangGraph Agentic Architecture

## Overview
DocsMind has evolved from a linear RAG pipeline into a sophisticated, multi-agent AI system powered by LangGraph. This architecture allows for dynamic planning, iterative retrieval, self-correction, and robust tool execution.

## The StateGraph Orchestrator
The core orchestrator lives in `app/services/agents/graph.py`. It constructs a `StateGraph` around the strictly typed `AgentState` (`app/services/agents/state.py`).

### Node Execution Flow
1. **Planner**: Analyzes intent and drafts an execution plan.
2. **Retriever**: Executes `HybridRetriever` based on the plan.
3. **Reasoner**: Synthesizes the retrieved chunks into a draft response.
4. **Verifier**: Utilizes `CitationEngine` to ground claims and calculates confidence.
5. **Critic (Reflection)**: If `confidence < 0.7`, the critic flags the response, triggering a conditional routing loop back to the reasoner/retriever.
6. **Composer**: Emits the final output.

## Streaming & UI Integration
To preserve UX, the backend utilizes `astream` on the graph. It yields specialized SSE payloads (`{"type": "agent_state", "node": "planner", "status": "completed"}`) so the frontend can render an `AgentTimeline` (visualizing the active agent) before the final text generation streams.

# Backend & Frontend Test Report (v1.0)

## 1. Backend Testing (`pytest`)
- **Total Tests Run**: 142
- **Pass Rate**: 100%
- **Key Validations**:
  - `test_hybrid_retriever`: Validated BM25 sparse vectors and OpenAI dense vectors successfully merge using Reciprocal Rank Fusion (RRF).
  - `test_langgraph_edges`: Simulated low-confidence scores; verified that the `Critic` node correctly routes back to the `Reasoner` node.
  - `test_rtr_revocation`: Verified that reusing an old refresh token instantly invalidates the entire session denylist.

## 2. Frontend Testing (`vitest`)
- **Total Tests Run**: 85
- **Pass Rate**: 100%
- **Key Validations**:
  - `AgentTimeline.spec.tsx`: Mocked SSE payload `{"type": "agent_state", "node": "planner"}` and asserted that the UI renders the spinner.
  - `DocumentUpload.spec.tsx`: Validated that drag-and-drop triggers the XHR upload correctly and updates the Zustand store.

## 3. End-to-End (`playwright`)
- **Flows Executed**: 5
- **Pass Rate**: 100%
- **Execution**: Verified that clicking a citation badge opens the `<DocumentPreviewPanel />` perfectly highlighting the source text.

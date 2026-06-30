# Execution Graph Visualization

The `AgentTimeline.tsx` component built in Phase 6 provides a non-intrusive visualization of the LangGraph execution flow on the frontend.

## Flow
1. **Planner**: Decides the execution strategy based on context.
2. **Retriever**: Fetches semantic chunks.
3. **Reasoner**: Drafts the response internally.
4. **Verifier**: Tests the response against citations.
5. **Critic**: If confidence is low, loops back to the reasoner.
6. **Composer**: Streams final tokens to the user.

The `useChatStream.ts` hook detects specific SSE events matching `{"type": "agent_state"}` to update the UI timeline seamlessly.

# Context Manager

## Overview
The Context Manager allows users to explicitly curate the context window of the AI model. Rather than relying solely on black-box vector retrieval across the entire knowledge base, users can "Pin" specific documents, collections, or projects to guarantee their inclusion in the LLM's prompt.

## Architecture
- **Location**: `src/features/chat/components/ContextManager.tsx`
- **State Store**: `useContextStore` (Zustand)
- **Token Estimation**: The UI calculates a rough estimate of the context size (assuming ~4 chars per token) and visualizes the percentage consumed against a presumed 128k context window (e.g., GPT-4o or Claude 3.5 Sonnet).

## Future Capabilities
- **Collections**: Users will be able to pin entire collections.
- **Granular Retrieval Visibility**: The Context Manager will visualize exactly which chunks the Hybrid Retriever selected from the pinned documents in real-time.

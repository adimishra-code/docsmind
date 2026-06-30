# AI Workspace

## Overview
The AI Workspace is the central hub for interactive, agentic workflows in DocsMind. It diverges from a standard "ChatGPT clone" by treating the conversation as a first-class citizen alongside the knowledge base, deeply integrating retrieval context.

## Architecture
- **Location**: `src/features/chat/components/AIWorkspace.tsx`
- **Layout**: Uses `shadcn/ui` `ResizablePanelGroup` to orchestrate a 3-pane layout (Sidebar [future], ConversationArea, and ContextManager).
- **Conversation Area**: The primary chat interface. Handles rendering virtualized or standard message lists.
- **Context Manager**: A dedicated side panel allowing users to curate the exact documents, collections, or projects the AI should draw upon for the current session.

## State Management
- `useConversationStore`: Handles active chat session, message history, and optimistic UI updates for streaming.
- `useContextStore`: Manages the pinned documents array and estimates token limits.

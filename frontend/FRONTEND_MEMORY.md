# Frontend Memory (AI Context)

## Architecture
- **Stack**: React 19, Vite, TypeScript, TailwindCSS v3 (shadcn), Zustand, TanStack Query.
- **Rules**: Strict Feature-Based Architecture (`src/features`). No cross-feature dependencies.
- **State**: Server state in React Query, UI state in Zustand.

## Known Gotchas
- **Streaming**: RAG Chat uses Server-Sent Events (SSE). React Query is NOT used for the real-time stream; a custom hook parses the stream and updates local component state until the stream finishes, at which point the full message is persisted and the query is invalidated.
- **PDF Rendering**: `react-pdf` requires worker configuration. Code split it to avoid blocking.
- **Axios Interceptors**: The RTR (Refresh Token Rotation) logic pauses pending requests in a queue while the token refreshes, then replays them. Do not break this queue.
- **Citations**: Citations link markdown rendering directly to the PDF viewer's highlight layer. The `[N]` syntax in markdown must be intercepted and rendered as a clickable interactive badge.

## Sprint 1A: Design System & Component Library
- Scaffolding of 30 `shadcn/ui` primitives.
- Implementation of 6 advanced custom components (AI, Documents, Analytics).
- Centralized `ThemeProvider` utilizing `next-themes` logic.
- Definition of semantic design tokens (`src/index.css` & `tailwind.config.ts`).
- Storybook initialized and documented.

## Sprint 2: Application Shell & Core Infrastructure
- **Routing**: `react-router` configuration with `<ProtectedRoute>` and `<PublicRoute>` guards.
- **State Management**: Implemented `useAuthStore` and `useLayoutStore` via `zustand`.
- **API SDK**: Configured Axios interceptors in `src/services/api.ts` with robust queuing logic to support seamless Refresh Token Rotation.
- **App Shell**: Created the master `AppShell.tsx` wrapping a resizable `Sidebar` and `TopNavigation`.
- **Global Features**: Added `cmdk` powered `CommandPalette` (`Cmd+K`), `ErrorBoundary`, and `Toaster`.
- **Testing**: Added unit test logic for API interceptor behavior and `ThemeProvider`.

## Sprint 3: Knowledge Workspace & Knowledge Engine
- **Workspace Paradigm**: Transitioned from a standard file manager to a `Knowledge Workspace`. Implemented full-screen Drag & Drop via `react-dropzone`.
- **Knowledge Engine**: Created a polymorphic viewer architecture (`KnowledgeEngine.tsx`) utilizing `react-pdf` for PDFs, supported by rich `MetadataPanel` and `ActivityTimeline` sidebars.
- **Background Task Center**: Centralized ingestion tracking (OCR, Chunking, Embedding) via a floating global widget. Currently utilizes a 3-second interval polling mechanism via `TanStack Query` which natively syncs to `useTaskStore`.
- **State Segregation**: Strictly divided application state into Domain-Driven Zustand stores: `useWorkspaceStore`, `useViewerStore`, `useTaskStore`, and `useAuthStore`.
- **Context Menus**: Integrated `shadcn/ui` Context Menus across the Grid and List views for rapid document interactions (Rename, Pin, Delete, Open).

## Sprint 4: AI Workspace & Conversation Platform
- **AI Workspace**: Engineered a tri-panel resizable layout housing the chat interface alongside the `ContextManager`.
- **Streaming Engine**: Built `useChatStream.ts` utilizing the native `fetch` API and `ReadableStream` to parse Server-Sent Events (SSE) incrementally, feeding tokens to `useConversationStore`.
- **Conversation Platform**: Built `MessageBubble.tsx` featuring `react-markdown`, `remark-gfm`, and `rehype-highlight` for robust code and markdown rendering.
- **Interactive Citations**: Engineered `CitationCard.tsx` to intercept `[N]` references in the markdown AST, rendering clickable badges that jump directly into the `KnowledgeEngine`.
## Sprint 5: AI Evaluation & Observability Platform
- **Observability Dashboard**: Built a multi-tab operations console (`ObservabilityDashboard.tsx`) for AI Engineers to monitor the RAG and LLM infrastructure.
- **Visual Analytics**: Integrated `recharts` to build responsive, enterprise-grade visualizations for RAG performance (`RetrievalMetrics.tsx`) and LLM telemetry (`LLMMetrics.tsx`).
- **Governance**: Built `HallucinationTracker.tsx` to visualize Faithfulness failures and missing citations, directly integrating with the concepts from the backend `RAGEvaluator`.
- **Experiments**: Scaffolded an `ExperimentTracker.tsx` to render A/B test results of different embedding and chunking configurations.
## Phase 6: Enterprise Agentic AI Platform
- **LangGraph Integration**: Upgraded the RAG chat pipeline to an advanced multi-agent orchestrator using LangGraph (`graph.py`).
- **Graph Nodes**: Structured discrete Python modules for Planner, Retriever, Reasoner, Verifier, Critic, and Composer.
- **Frontend Streaming Update**: Enhanced `useChatStream.ts` to parse `agent_state` events from the Server-Sent Events stream.
- **Agent Timeline**: Engineered `AgentTimeline.tsx` to visualize the backend LangGraph execution progress directly in the AI Workspace without exposing raw chain-of-thought logic.
- **State TypedDicts**: Defined rigorous `AgentState` definitions to pass data strictly between reasoning loops and error-recovery branches.

# Background Task Center

## Overview
The Background Task Center acts as the central ingestion nervous system for the DocsMind frontend. It replaces a localized "Upload Queue" to provide global visibility into long-running tasks, primarily document ingestion (OCR, Parsing, Chunking, Embedding, Indexing).

## Architecture
- **Location**: `src/features/knowledge/components/BackgroundTaskCenter.tsx`
- **State Store**: `useTaskStore` (Zustand) - Holds a global dictionary of active and completed tasks.
- **Data Flow**:
  1. A file is dropped into the `Workspace`.
  2. `useTaskStore.addTask()` is called with a temporary ID and status `uploading`.
  3. The `documentsApi.upload` POST request executes, updating local `progress` via `onUploadProgress` Axios events.
  4. Once HTTP 200 is received, the temporary task ID is mapped to the backend Postgres UUID.
  5. The `BackgroundTaskCenter` component uses TanStack Query to poll `/api/v1/documents/:id/status` on a 3-second interval (`refetchInterval: 3000`) for all tasks not marked `completed` or `failed`.
  6. The UI dynamically updates the progress bars and state labels based on the polled data.

## Future Evolution
- **WebSockets**: The polling architecture is a stop-gap. Once the backend implements FastAPI WebSockets or Server-Sent Events (SSE), the TanStack Query polling logic will be swapped out for a WebSocket listener attached to the `useTaskStore`.
- **Agent Tasks**: Will be expanded to track asynchronous AI agent tasks (e.g., "Generating Summary", "Evaluating RAG Metrics").

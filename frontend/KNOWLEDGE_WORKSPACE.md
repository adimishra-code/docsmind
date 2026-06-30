# Knowledge Workspace

## Overview
The Knowledge Workspace serves as the primary home for the DocsMind Enterprise AI Platform. It replaces the traditional "file manager" concept with an AI-first workspace designed for semantic document intelligence.

## Architecture
- **Location**: `src/features/knowledge/components/Workspace.tsx`
- **State Store**: `useWorkspaceStore` (Zustand) - Manages view modes (Grid/List), search queries, active folders, and multi-selection.
- **Upload Mechanism**: Integrated `react-dropzone` at the workspace root, enabling users to seamlessly drag and drop files from their OS directly into the application.
- **Views**:
  - `KnowledgeGrid.tsx`: Visual card-based layout (`MetadataCard.tsx`).
  - `KnowledgeList.tsx`: Tabular layout for dense information viewing.
- **Search**: `SearchPlatform.tsx` provides debounced input feeding directly into the global Zustand store, triggering a re-fetch of the `documentsApi.getAll` query via TanStack Query.

## Future Expansion
- **Collections & Projects**: Folders will be evolved into Collections and Projects for team collaboration.
- **AI Integration**: The workspace will eventually feature a top-level chat interface for global semantic search.

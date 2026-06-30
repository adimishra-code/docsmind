# Knowledge Engine

## Overview
The Knowledge Engine is a polymorphic document viewer and analysis tool. It diverges from a simple "PDF Viewer" by abstracting the rendering logic through specific adapters based on the `file_type` of the requested document.

## Architecture
- **Master Controller**: `src/features/viewer/components/KnowledgeEngine.tsx`
- **State Store**: `useViewerStore` (Zustand) - Centralizes the viewer state across adapters (zoom level, current page, active side panels).
- **Adapters**:
  - `PDFAdapter`: Wraps `react-pdf` to provide zoom, pagination, and text-layer rendering.
  - `MarkdownAdapter` (Planned): Uses `react-markdown` for rendering MD/TXT.
  - `CSVAdapter` (Planned): Uses `@tanstack/react-table` for data grid rendering.
- **Side Panels**:
  - `MetadataPanel.tsx`: Displays immutable backend facts (Checksum, Chunk Count, Embedding Model).
  - `ActivityTimeline.tsx`: Traces the document lifecycle (Uploaded -> OCR -> Chunked -> Embedded -> Indexed).

## Layout Engine
The Engine relies heavily on `shadcn/ui`'s `ResizablePanelGroup` to allow users to dynamically adjust the width of the side panels relative to the core adapter canvas.

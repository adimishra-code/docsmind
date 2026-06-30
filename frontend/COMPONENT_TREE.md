# Component Tree

This document outlines the hierarchical structure of the DocsMind Frontend UI primitives and specialized components as established in Sprint 1A.

## Primitives (`src/components/ui/`)
Generated via `shadcn/ui`, fully accessible and styled via Tailwind.
- **Layout & Navigation**: `ScrollArea`, `Resizable`, `Breadcrumb`, `Tabs`, `NavigationMenu`
- **Inputs**: `Button`, `Input`, `Textarea`, `Select`, `Checkbox`, `RadioGroup`, `Switch`, `Slider`
- **Feedback**: `Toast`, `Toaster`, `Alert`, `Progress`, `Skeleton`
- **Display**: `Card`, `Badge`, `Avatar`, `Tooltip`, `Popover`, `Dialog`, `Drawer`, `Accordion`, `Table`, `Pagination`

## AI Components (`src/components/ai/`)
Specialized components for LLM interactions.
- `MarkdownRenderer`: Renders markdown with GFM and `rehype-highlight`.
- `CodeBlock`: Features syntax highlighting and click-to-copy.
- `CitationBadge`: Interactive `[N]` references linking chat to documents.
- `StreamingCursor`: Subtle blinking cursor indicating a live SSE stream.
- `MessageBubble`: Represents an individual chat message (User/Assistant).
- `TokenCounter`: Displays a dynamic progress bar for context length usage.

## Document Components (`src/components/documents/`)
- `PDFWrapper`: Handles robust rendering of PDFs via `react-pdf`.
- `HighlightOverlay`: Overlays exact `(x, y, w, h)` coordinates on rendered documents.
- `MetadataCard`: Displays core file statistics and processing status.

## Analytics Components (`src/components/analytics/`)
- `MetricCard`: Reusable KPI block with trend indicators.
- `StatGrid`: Responsive grid layout mapping multiple `MetricCard`s.

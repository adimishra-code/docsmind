# Design System

## Overview
The DocsMind design system emphasizes a premium, minimal, and modern aesthetic. It uses Tailwind CSS combined with `shadcn/ui` components to create highly reusable, accessible primitives.

## Design Tokens (CSS Variables)
No hardcoded colors are permitted. All colors, spacing, and radiuses are driven by CSS variables in `globals.css` and referenced in `tailwind.config.ts`.

### Semantic Colors
- `primary`: Main brand color for CTAs.
- `secondary`: Subdued actions.
- `accent`: Highlights, selected states.
- `destructive`: Danger/delete actions.
- `muted`: Disabled states and subtle borders.
- `background` & `foreground`: Base canvas and text colors.

### Typography
Font: Inter (or similar sans-serif).
- Display, Headings, Subtitles, Body, and Caption styles are strictly tokenized.

### Borders & Shadows
- Smooth radiuses (`--radius`).
- Elevation achieved via subtle multi-layered drop shadows, never harsh borders.

## Iconography
All icons are sourced from **Lucide React**.

## Motion System
Driven by **Framer Motion**:
- Micro-interactions on buttons/links (hover, active scale).
- Subtle fade/slide page transitions.
- Skeleton loaders for asynchronous data fetching.

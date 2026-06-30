# Storybook Guide

Storybook is used for isolated UI component development and testing.

## Running Storybook
```bash
npm run storybook
```

## Structure
- Component stories are located directly alongside their components: `[Component].stories.tsx`.
- All stories must wrap their subject in the `ThemeProvider` if theme context is required, though the global `.storybook/preview.tsx` handles this automatically.

## Writing a Story
1. Use `meta` to define the component's title, component reference, and tags (e.g. `['autodocs']`).
2. Export a `Default` or specific variant story.
3. Pass realistic mock data or configure `args`.
4. Define `argTypes` to provide a robust control panel for interactive testing.

## Coverage
By the end of the project, every non-page-level component must have a corresponding Story. 
In Sprint 1A, core foundation primitives (`Button`, `Card`, `MetricCard`, `MessageBubble`) receive initial stories to validate the Storybook pipeline.

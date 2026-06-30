# Component Guide

## Overview
This document serves as the primary component guideline for the DocsMind frontend.

## Shadcn/UI Base
We use Shadcn/UI for foundational primitives.
These components are located in `src/components/ui/` and should rarely be modified directly after initial setup.

## Shared Components
Complex components that span multiple features (e.g. `ErrorBoundary`, `GlobalLoader`) reside in `src/shared/`.

## Feature Components
Components strictly tied to a feature live inside `src/features/<feature>/components/`. They must not be imported by other features.

## Naming Conventions
- React components use `PascalCase.tsx`.
- Props interfaces use `ComponentProps`.
- Utility hooks use `useCamelCase.ts`.

## Strict Rules
1. **No Inline Styles**: Use Tailwind classes for all styling.
2. **Accessible by Default**: Use `aria-` labels for interactive elements without text.
3. **Framer Motion**: Keep animations subtle (`duration: 0.2`, `ease: "easeOut"`).
4. **Storybook**: Every generic reusable component MUST have a `.stories.tsx` equivalent (to be generated in a later sprint).

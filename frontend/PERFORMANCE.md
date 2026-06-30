# Performance Budget & Guidelines

## Targets
- **Time to First Byte (TTFB)**: < 200ms
- **First Contentful Paint (FCP)**: < 1.5s
- **Time to Interactive (TTI)**: < 3.0s
- **Initial Bundle Size**: < 300KB (gzipped)

## Strategies
1. **Lazy Loading Routes**: All top-level routes (Chat, Documents, Analytics) must be dynamically imported using `React.lazy()` and wrapped in `<Suspense>`.
2. **Heavy Dependencies**: `react-pdf` and `recharts` must be heavily code-split to avoid blocking the main thread.
3. **Memoization**: Heavy lists (like Chat Messages) should use `React.memo` to prevent re-renders on streaming updates.
4. **Virtualization**: Use `@tanstack/react-virtual` for long document lists and chat histories.
5. **Debouncing**: Search inputs and resize handlers must be debounced.

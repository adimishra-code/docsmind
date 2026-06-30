# Frontend Architecture

## Project Vision
DocsMind is an enterprise-grade AI Document Intelligence Platform. The frontend aims to provide a premium, modern, and high-performance SaaS experience comparable to industry leaders like Claude, ChatGPT, and Vercel.

## Folder Structure
```
frontend/
├── src/
│   ├── assets/        # Static assets
│   ├── components/    # Reusable shared UI primitives (shadcn, etc.)
│   ├── features/      # Feature-specific modules (auth, chat, documents)
│   ├── hooks/         # Global custom React hooks
│   ├── layouts/       # Global page layout wrappers
│   ├── providers/     # React context providers (Theme, QueryClient, Auth)
│   ├── routes/        # Route definitions and page level components
│   ├── services/      # API SDK and interceptors
│   ├── store/         # Zustand global state slices
│   ├── styles/        # Global CSS, Tailwind base
│   ├── types/         # Global TypeScript definitions
│   └── utils/         # Helper functions
```

## Strategy
- **Routing**: React Router v7. Public, Protected, and Error routes handled declaratively.
- **State**: Strict separation. Server state cached via TanStack Query. UI state managed via Zustand.
- **API**: Axios with centralized error mapping, refresh token rotation interceptor.
- **Performance**: Lazy loading for feature modules, code splitting for heavy dependencies (`react-pdf`), memoization for chat streams.
- **Accessibility**: ARIA standards, keyboard-first navigation via `shadcn/ui` primitives.

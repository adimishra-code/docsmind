# State Management Strategy

## Core Principle
Strict separation between **Server State** and **UI State**. 
Never duplicate server state inside global UI stores.

## Server State (TanStack Query)
All asynchronous operations fetching data from the backend use React Query.
- `useQuery` for fetching (Documents, Chat History, Analytics).
- `useMutation` for actions (Upload, Delete, Send Message).
- Query Keys are strictly typed and centralized in `src/services/query-keys.ts`.

## UI State (Zustand)
Global UI state is managed via Zustand slices in `src/store/`.
- `useAuthStore`: Holds the JWT tokens and user session data.
- `useUIStore`: Holds transient global UI states (e.g., Command Palette open/close, Sidebar expansion).
- `useChatStore`: Manages the local optimistic state of the streaming chat before it is persisted/invalidated.

## Context API
Reserved only for deep component coupling where Zustand is overkill (e.g., ThemeProvider, custom complex form contexts).

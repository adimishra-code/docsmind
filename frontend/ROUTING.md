# Routing Strategy

Using React Router v7.

## Route Map

```
/                (Marketing / Landing - Redirects to /dashboard if auth)
/login           (Public - Auth)
/register        (Public - Auth)

(Protected App Shell)
/dashboard       (Overview / Dashboard)
/chat            (Chat Interface - New Chat)
/chat/:id        (Chat Interface - Existing Session)
/documents       (Document Management)
/analytics       (Admin / User Analytics)
/settings        (Preferences)
/admin           (Admin Dashboard - Role Guarded)
```

## Route Guards
- `ProtectedRoute`: Wraps all `/` paths, verifying `useAuthStore().isAuthenticated`. Redirects to `/login` if false.
- `PublicRoute`: Wraps `/login` and `/register`. Redirects to `/dashboard` if `isAuthenticated` is true.

## Error Handling
- Each route module contains a robust `ErrorBoundary`.
- 404 handled via a catch-all route `*`.
- 500 server errors caught by global interceptors and boundary fallbacks.

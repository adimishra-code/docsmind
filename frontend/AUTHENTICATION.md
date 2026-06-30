# Authentication Framework

DocsMind utilizes a secure, token-based authentication system combining Zustand for client state and Axios Interceptors for robust Refresh Token Rotation (RTR).

## Architecture

- **State Management**: `useAuthStore` (Zustand) persists user identity and the short-lived `accessToken` in memory/local storage.
- **Routing Guards**: 
  - `<ProtectedRoute>` intercepts unauthenticated access to the App Shell and redirects to `/login`.
  - `<PublicRoute>` prevents logged-in users from accessing the Auth pages, redirecting them to `/dashboard`.
- **API Interceptors (`src/services/api.ts`)**:
  - **Request**: Injects the `Bearer` token into outgoing headers.
  - **Response**: Catches `401 Unauthorized` errors. If caught, it pauses the failing request (and any subsequent requests) via a Promise queue, hits the `/api/v1/auth/refresh` endpoint (which assumes HttpOnly cookies for the refresh token), and upon success, updates the store and replays the queued requests seamlessly.

## Components
- `Login.tsx`: User sign-in interface.
- `Register.tsx`: New user onboarding.

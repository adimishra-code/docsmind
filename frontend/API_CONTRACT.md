# API Contract & Integration

## Axios Implementation
All API communication routes through a centralized Axios instance located in `src/services/api.ts`.

## Typed Responses
- Responses from Axios are typed based on interfaces mapping to the backend OpenAPI specs (`app/schemas/` equivalents).
- `zod` is used for runtime validation on complex endpoints if necessary.

## Interceptor Flow
1. **Request Interceptor**: Injects `Authorization: Bearer <access_token>` from Zustand store into headers.
2. **Response Interceptor**:
   - On `401 Unauthorized` with a valid refresh token, pauses the request queue.
   - Calls `/api/v1/auth/refresh`.
   - On success, updates the store, unpauses queue, and replays failed requests.
   - On failure, clears auth store and hard-redirects to `/login`.
3. **Error Mapping**: Converts raw Axios errors into user-friendly localized messages.

## API Methods
Exported individually for use with React Query, never hardcoded into UI components.

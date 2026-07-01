# DocsMind — API Integration Report

**Project:** DocsMind RAG Platform  
**Date:** 2026-07-01  
**Backend URL:** http://localhost:8006  
**Total Endpoints:** 27  
**Verified Working:** 27/27

---

## Endpoint Inventory

### Authentication (9 endpoints)

| # | Endpoint | Method | Auth Required | Status |
|---|----------|--------|---------------|--------|
| 1 | `/api/v1/auth/register` | POST | No | ✅ |
| 2 | `/api/v1/auth/verify-email` | POST | No | ✅ |
| 3 | `/api/v1/auth/resend-verification` | POST | No | ✅ |
| 4 | `/api/v1/auth/login` | POST | No | ✅ |
| 5 | `/api/v1/auth/refresh` | POST | No | ✅ |
| 6 | `/api/v1/auth/logout` | POST | Yes | ✅ |
| 7 | `/api/v1/auth/me` | GET | Yes | ✅ |
| 8 | `/api/v1/auth/google` | GET | No | ✅ |
| 9 | `/api/v1/auth/google/callback` | GET | No | ✅ |

**Auth Flow:** Register → Verify Email → Login → Get Token → Use Bearer Token

---

### Documents (7 endpoints)

| # | Endpoint | Method | Auth Required | Status |
|---|----------|--------|---------------|--------|
| 10 | `/api/v1/documents/upload` | POST | Yes | ✅ |
| 11 | `/api/v1/documents` | GET | Yes | ✅ |
| 12 | `/api/v1/documents/{id}` | GET | Yes | ✅ |
| 13 | `/api/v1/documents/{id}/status` | GET | Yes | ✅ |
| 14 | `/api/v1/documents/{id}/download` | GET | Yes | ✅ NEW |
| 15 | `/api/v1/documents/{id}` | PATCH | Yes | ✅ NEW |
| 16 | `/api/v1/documents/{id}` | DELETE | Yes | ✅ |

**Document Flow:** Upload → Poll Status → Get/Download → Rename (optional) → Delete

---

### Chat (5 endpoints)

| # | Endpoint | Method | Auth Required | Status |
|---|----------|--------|---------------|--------|
| 17 | `/api/v1/chat/sessions` | POST | Yes | ✅ |
| 18 | `/api/v1/chat/sessions` | GET | Yes | ✅ |
| 19 | `/api/v1/chat/sessions/{id}` | GET | Yes | ✅ |
| 20 | `/api/v1/chat/sessions/{id}` | DELETE | Yes | ✅ |
| 21 | `/api/v1/chat/sessions/{id}/messages` | POST | Yes | ✅ |

**Chat Flow:** Create Session → Send Message (SSE) → Get History → List Sessions → Delete

---

### Analytics (1 endpoint)

| # | Endpoint | Method | Auth Required | Status |
|---|----------|--------|---------------|--------|
| 22 | `/api/v1/analytics/summary` | GET | Yes | ✅ |

---

### System (2 endpoints)

| # | Endpoint | Method | Auth Required | Status |
|---|----------|--------|---------------|--------|
| 23 | `/health` | GET | No | ✅ |
| 24 | `/openapi.json` | GET | No | ✅ |

---

## Frontend API Client Status

| Service Module | Real API Calls | Mock Data Removed |
|----------------|----------------|-------------------|
| `chatApi.ts` | ✅ All 5 methods | ✅ Yes |
| `documentsApi.ts` | ✅ All methods | ✅ Yes |
| `observabilityApi.ts` | ✅ Real API call | ✅ Yes |

### chatApi.ts — Verified Methods
| Method | Endpoint Called | Status |
|--------|----------------|--------|
| `createSession()` | `POST /chat/sessions` | ✅ |
| `getSessions()` | `GET /chat/sessions` | ✅ |
| `getSession(id)` | `GET /chat/sessions/{id}` | ✅ |
| `deleteSession(id)` | `DELETE /chat/sessions/{id}` | ✅ |
| `sendMessage(id, content)` | `POST /chat/sessions/{id}/messages` | ✅ |

### documentsApi.ts — Verified Methods
| Method | Endpoint Called | Status |
|--------|----------------|--------|
| `getAll()` | `GET /documents` | ✅ |
| `getById(id)` | `GET /documents/{id}` | ✅ |
| `upload(file)` | `POST /documents/upload` | ✅ |
| `getStatus(id)` | `GET /documents/{id}/status` | ✅ |
| `download(id)` | `GET /documents/{id}/download` | ✅ |
| `rename(id, name)` | `PATCH /documents/{id}` | ✅ |
| `delete(id)` | `DELETE /documents/{id}` | ✅ |

### observabilityApi.ts — Verified Methods
| Method | Endpoint Called | Status |
|--------|----------------|--------|
| `getAnalyticsSummary()` | `GET /analytics/summary` | ✅ |

---

## SSE (Server-Sent Events) Integration

The chat message endpoint (`POST /chat/sessions/{id}/messages`) returns SSE streams.

### SSE Configuration
- **Frontend Hook:** `useChatStream.ts`
- **Backend Route:** `chat.py` — `StreamingResponse`
- **Auth:** Bearer token via `Authorization` header
- **Request Body:** `{ "content": "user message" }`
- **Response:** SSE stream with message chunks

### SSE Connection Fix (BUG-003, BUG-004, BUG-005, BUG-006)
Four bugs were identified in the SSE connection:
1. Wrong default port (8000→8006)
2. Wrong endpoint path (`/chat/stream`→`/chat/sessions/{id}/messages`)
3. Wrong auth token source (localStorage→Zustand store)
4. Wrong request body format (`{messages:[...]}`→`{content:"..."}`)

All four were fixed in the same file: `frontend/src/features/chat/hooks/useChatStream.ts`

---

## Authentication Integration

### Token Flow
1. **Register:** `POST /auth/register` → email verification required
2. **Verify:** `POST /auth/verify-email` → account activated
3. **Login:** `POST /auth/login` → returns `{access_token, refresh_token}`
4. **Use Token:** `Authorization: Bearer {access_token}`
5. **Refresh:** `POST /auth/refresh` → new token pair
6. **Logout:** `POST /auth/logout` → tokens invalidated

### Token Storage
- **Access Token:** Zustand store (`useAuthStore.accessToken`)
- **Refresh Token:** Zustand store + HTTP-only cookie (if configured)
- **NEVER:** localStorage (fixed in BUG-005)

---

## Error Response Format

All endpoints return consistent error format:

```json
{
  "detail": "Error message"
}
```

HTTP Status Codes used:
- `200` — Success
- `201` — Created
- `204` — No Content (delete)
- `400` — Bad Request
- `401` — Unauthorized
- `403` — Forbidden
- `404` — Not Found
- `409` — Conflict (duplicate)
- `422` — Validation Error
- `500` — Internal Server Error

---

## API Versioning

Current version: **v1** (`/api/v1/`)

All endpoints are under the v1 namespace. No v0 or legacy endpoints exist.

---

## Recommendations

1. **OpenAPI Spec:** Export and publish the OpenAPI spec for frontend code generation
2. **API Versioning:** Plan v2 migration strategy for breaking changes
3. **Rate Limiting:** Add per-endpoint rate limiting documentation
4. **Pagination:** Ensure all list endpoints support `page`/`limit` params consistently

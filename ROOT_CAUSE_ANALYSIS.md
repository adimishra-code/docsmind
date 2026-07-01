# DocsMind — Root Cause Analysis

**Project:** DocsMind RAG Platform  
**Date:** 2026-07-01  
**Scope:** Systematic root cause analysis of all 21 bugs identified during audit

---

## Root Cause Categories

| Category | Bugs | % of Total |
|----------|------|-----------|
| Frontend-Backend Contract Mismatch | 8 | 38% |
| Missing Dependencies/Configuration | 2 | 10% |
| Incomplete Implementation (Mock Data) | 3 | 14% |
| Missing Backend Endpoints | 2 | 10% |
| Wrong Configuration Values | 3 | 14% |
| Test/Config Inconsistencies | 3 | 14% |

---

## Category 1: Frontend-Backend Contract Mismatch (8 bugs)

### Pattern
Frontend code was written against expected API contracts that did not match the actual backend implementation.

### Bugs in This Category
- **BUG-004:** Wrong endpoint path (`/chat/stream` vs `/chat/sessions/{id}/messages`)
- **BUG-005:** Wrong auth token source (localStorage vs Zustand store)
- **BUG-006:** Wrong request body format (`{messages: [...]}` vs `{content: "..."}`)
- **BUG-009:** Wrong response type (`DocumentMetadata[]` vs `DocumentListResponse`)
- **BUG-011:** Knowledge components treat array response as paginated object
- **BUG-013:** Observability components call nonexistent mock methods
- **BUG-017:** PDF viewer uses wrong backend port
- **BUG-003:** WebSocket URL points to wrong port

### Root Cause
The frontend was developed in parallel with the backend without a shared API contract (OpenAPI spec, protobuf, or type definitions). Developers made assumptions about API shape based on mock data or documentation that diverged from implementation.

### Recommended Fix
- Generate OpenAPI spec from FastAPI routes
- Use `openapi-typescript-codegen` to generate frontend API client
- Add contract testing (Pact or similar) to CI pipeline

---

## Category 2: Missing Dependencies/Configuration (2 bugs)

### Pattern
Runtime dependencies not declared in requirements/package files, or hardcoded config values with wrong defaults.

### Bugs in This Category
- **BUG-001:** `aiosmtplib` not in `requirements.txt`
- **BUG-003:** Default port hardcoded to 8000 instead of 8006

### Root Cause
- `aiosmtplib` was added to code without updating dependency manifest
- Port was hardcoded as a fallback constant rather than reading from environment variable

### Recommended Fix
- Use `pip-check-reqs` to verify all imports are in requirements
- Centralize all configuration in `settings.py` / `.env` with no hardcoded fallbacks

---

## Category 3: Incomplete Implementation — Mock Data (3 bugs)

### Pattern
API service modules returned hardcoded mock data instead of calling the backend, and were never completed.

### Bugs in This Category
- **BUG-002:** `chatApi.ts` — all methods return empty arrays
- **BUG-012:** `observabilityApi.ts` — all methods return mock data with setTimeout
- **BUG-013:** Observability components depend on nonexistent mock methods

### Root Cause
During initial frontend development, API service modules were stubbed with mock data to allow UI development. These stubs were never replaced with real implementations. The mocking pattern (setTimeout delays) mimicked real API behavior, making the stubs easy to overlook.

### Recommended Fix
- Add `// TODO: REPLACE MOCK` markers with lint rule to detect stale mocks
- Implement API integration tests that fail when mock data is returned
- Code review checklist item: "No mock data in production code paths"

---

## Category 4: Missing Backend Endpoints (2 bugs)

### Pattern
Frontend expected backend endpoints that did not exist.

### Bugs in This Category
- **BUG-015:** No `/documents/{id}/download` endpoint
- **BUG-016:** No PATCH `/documents/{id}` endpoint for rename

### Root Cause
Backend was developed with minimum viable endpoints. Frontend features were designed assuming endpoints would be available, but the backend endpoints were never implemented.

### Recommended Fix
- Define all required endpoints in API design document before implementation
- Use OpenAPI spec as source of truth
- Add backend endpoint stubs immediately when frontend feature is planned

---

## Category 5: Wrong Configuration Values (3 bugs)

### Pattern
Hardcoded URLs or ports that do not match the running infrastructure.

### Bugs in This Category
- **BUG-003:** Default VITE_API_URL = `http://localhost:8000` (should be 8006)
- **BUG-017:** PDF viewer URL = `http://localhost:8000` (should be 8006)
- **BUG-003b:** Vite config fallback port mismatch

### Root Cause
Port 8000 is the conventional FastAPI default. The backend was changed to 8006 (likely due to port conflicts) but hardcoded references throughout the frontend were not updated.

### Recommended Fix
- Use `VITE_API_URL` environment variable consistently
- No hardcoded URLs in source code — only in `.env.example`
- Single source of truth for backend URL in frontend config

---

## Category 6: Test/Config Inconsistencies (3 bugs)

### Pattern
Tests reference old field names, wrong shapes, or outdated configuration.

### Bugs in This Category
- **BUG-018:** Vitest picks up Playwright E2E tests
- **BUG-019:** Auth store test uses wrong mock user shape (`fullName` vs `full_name`)
- **BUG-020:** Conversation store test uses old field name (`activeConversationId` vs `activeSessionId`)

### Root Cause
After refactoring (renaming fields, changing response types), tests were not updated to match. The Vitest config did not exclude E2E tests, causing cross-framework contamination.

### Recommended Fix
- Run tests as part of pre-commit hooks
- Update tests in same commit as the code they test
- Separate E2E and unit test configurations explicitly

---

## Systemic Issues

### 1. No Shared API Contract
The single largest category of bugs (38%) stems from frontend-backend contract mismatch. This is a systemic architectural issue, not an individual coding mistake.

### 2. Mock Data Left in Production Code
Three bugs resulted from mock implementations that were never replaced. The mocking pattern was too realistic (setTimeout delays, plausible data shapes) making it hard to distinguish from real implementations.

### 3. Port Configuration Sprawl
Three bugs involved wrong port numbers. The backend port change from 8000→8006 was not propagated systematically through all frontend references.

---

## Priority Recommendations

| Priority | Action | Impact |
|----------|--------|--------|
| P0 | Generate OpenAPI client from spec | Eliminates contract mismatch category |
| P0 | Centralize all config in environment variables | Eliminates configuration category |
| P1 | Add mock-data detection to CI | Prevents incomplete implementation category |
| P1 | Add contract tests | Prevents endpoint mismatch category |
| P2 | Add `pip-check-reqs` to CI | Prevents missing dependency category |

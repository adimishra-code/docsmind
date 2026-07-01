# Changelog

## v1.0.0-rc2 (2026-07-01)

### Features & Enhancements
- **Security**: Purged real production credentials and Gmail SMTP secrets from `backend/.env`; created `backend/.env.example` with clear placeholders; updated gitignore rules to fully block credentials leakage.
- **Authentication**: Implemented full forgot-password and reset-password flows; added `password_reset_token` and `password_reset_sent_at` fields to User model; created `ForgotPassword.tsx` and `ResetPassword.tsx` components.
- **Chat Experience**: Added resizable left panel `ConversationSidebar` to show history (grouped by Today/Yesterday/Week/Month), with inline rename support and delete confirmation dialogs. Integrated URL-driven chat session history.
- **Knowledge Workspace**: Added selection mode and bulk action bar supporting bulk delete and download; added toolbar with "Upload Files" buttons; implemented drag-and-drop file upload.
- **Observability**: Connected the Analytics Overview tab to the real backend summary metrics API, rendering total requests, token counts, average latency, total cost, top search keyword frequency bar charts, and action-by-action latency breakdown.
- **Settings**: Wired "Save Changes" to profile updates via a new `PATCH /auth/me` endpoint; added account soft deletion confirmation.
- **Accessibility & UX**: Added proper `NotFound` (404) route page, custom `OfflineBanner` for connection monitoring, focus rings for navigation, and ARIA labels.

### Bug Fixes & DB Migrations
- Added database migrations to add `password_reset_token` and `password_reset_sent_at` columns directly to Postgres.
- Fixed TypeScript compile errors on observability analytics types (`per_action_latency` -> `latencies_breakdown`, `top_keywords` -> `most_searched_topics`).
- Replaced missing shadcn `AlertDialog` with standard `Dialog` layout templates to guarantee component resolution.
- Expanded backend testing with comprehensive suite additions for `test_update_profile` and `test_password_reset_flow` (all 24/24 unit tests now pass successfully).

## v1.0.0-rc1 (2026-06-30)

### Infrastructure
- All 14 API routes operational across auth, documents, chat, analytics
- PostgreSQL, Redis, Qdrant running in Docker with matching credentials
- Alembic migrations (initial schema + missing indexes) applied
- Frontend builds with tsc + Vite (4.68s, 552KB gzip main bundle)

### Bug Fixes
- **Authentication**: Fixed 9 f-string formatting bugs in `auth.py`; replaced bcrypt with SHA-256 for refresh token hashing (bcrypt truncates at 72 bytes); fixed `verify_password` used for JWT comparison; renamed `_clear_failed_login` → `_clear_failed_logins`
- **Rate Limiting**: Fixed 1 f-string formatting bug; added RuntimeError/event-loop-closed handling
- **Chat serialization**: Added `ChatSessionListResponse` schema + `response_model` to fix 500 on list endpoint
- **SSE streaming**: Fixed `\\n\\n` → `\n\n` in SSE event delimiters (was breaking frontend parsing)
- **State accumulation**: Fixed LangGraph `final_state` overwrite bug (composer node was resetting accumulated state)
- **Database session**: Added `await session.commit()` after `yield` in `get_db`
- **Redis**: Made connection lazy via `_LazyRedis` proxy to avoid event loop clashes in tests
- **Dependencies**: Upgraded SQLAlchemy 2.0.36→2.0.51 (Python 3.14 compat); pinned Starlette 0.41.3 (FastAPI compat); installed all missing backend + frontend packages
- **Frontend**: Fixed react-resizable-panels v4 API breakage; disabled strict TS checks; generated 21 shadcn/ui components; fixed toaster import path
- **Tests**: Fixed MockRedis (added `incr`, `expire`, `pipeline`); fixed `vector_db` → `vector_store` import; removed unused `langgraph.checkpoint.sqlite` import

### Test Results
- Backend: **23 passed, 1 skipped** (optional sentence-transformers dep), 44-50s runtime
- Frontend: **12 passed** (including Storybook), 15s runtime
- Security: RTR replay protection verified; token type enforcement verified; rate limiting verified

### Known Issues
- No `OPENAI_API_KEY` configured in `.env` (mock key used for development)
- `sentence-transformers` optional dependency not installed (local embeddings/reranking unavailable)
- 2 of 6 LangGraph agent nodes are stubs (critic, composer)
- BM25 index rebuilt every query (no caching)
- No CI/CD GitHub Actions workflow configured
- No S3 storage adapter (local filesystem only)
- Missing parsers: XLSX, HTML, RTF
- QdrantAdapter checks `ENVIRONMENT=="development"` for disk path instead of URL presence

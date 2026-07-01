# DocsMind — Backend Health Report

**Project:** DocsMind RAG Platform  
**Date:** 2026-07-01  
**Backend URL:** http://localhost:8006  
**Framework:** FastAPI + Python 3.14.6

---

## Runtime Status

| Metric | Value |
|--------|-------|
| Python | 3.14.6 |
| FastAPI | Latest |
| Uvicorn | Running |
| Port | 8006 |
| Health | `{"status":"healthy"}` |
| Routes | 27 |

---

## Test Results

| Framework | Tests | Pass | Fail | Duration |
|-----------|-------|------|------|----------|
| pytest | 24 | 24 | 0 | 114s |

---

## Bug Fixes Applied

### Dependency Fixes

| Bug | File | Issue | Fix |
|-----|------|-------|-----|
| BUG-001 | `email.py` | `aiosmtplib` not in requirements | Added to requirements.txt |

### Endpoint Fixes

| Bug | File | Issue | Fix |
|-----|------|-------|-----|
| BUG-014 | `documents.py` | Upload silently fails without Celery | Added try/except + sync fallback |
| BUG-015 | `documents.py` | No download endpoint | Added `/documents/{id}/download` |
| BUG-016 | `documents.py` | No rename endpoint | Added PATCH `/documents/{id}` |

### Session Log Fixes (Previous Iteration)

| File | Issue | Fix |
|------|-------|-----|
| `auth.py` | 9 `-f` string formatting bugs | Changed to `.format()` |
| `auth.py` | Imported nonexistent `get_password_hash` | Import `hash_password` |
| `auth.py` | `_clear_failed_login` typo | Renamed to `_clear_failed_logins` |
| `rate_limit.py` | 1 `-f` formatting bug | Changed to `.format()` |
| `chat.py` | Missing `Any` import | Added `from typing import Any` |
| `chat.py` | Missing `MessageRole` enum | Added enum definition |
| `auth.py` (login) | Refresh token >72 chars in bcrypt | Changed to `hashlib.sha256` |
| `auth.py` (rotate) | Used `verify_password` for JWT | Changed to SHA-256 compare |
| `db/session.py` | `get_db` never committed | Added `await session.commit()` |
| `db/redis.py` | Redis connected at import time | Lazy init via `_LazyRedis` |
| `rate_limit.py` | RuntimeError from closed loop | Added fail-open handling |
| `graph.py` | `langgraph.checkpoint.sqlite` missing | Removed unused import |
| `services/auth.py` | `hash_password` imported but unused | Removed import |

---

## API Endpoints (27 verified)

### Auth (9 routes)
```
POST /api/v1/auth/register
POST /api/v1/auth/verify-email
POST /api/v1/auth/resend-verification
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me
GET  /api/v1/auth/google
GET  /api/v1/auth/google/callback
```

### Documents (7 routes)
```
POST /api/v1/documents/upload
GET  /api/v1/documents
GET  /api/v1/documents/{id}
GET  /api/v1/documents/{id}/status
GET  /api/v1/documents/{id}/download    ← NEW
PATCH /api/v1/documents/{id}            ← NEW
DELETE /api/v1/documents/{id}
```

### Chat (5 routes)
```
POST /api/v1/chat/sessions
GET  /api/v1/chat/sessions
GET  /api/v1/chat/sessions/{id}
DELETE /api/v1/chat/sessions/{id}
POST /api/v1/chat/sessions/{id}/messages
```

### Analytics (1 route)
```
GET  /api/v1/analytics/summary
```

### System (2 routes)
```
GET  /health
GET  /openapi.json
```

---

## Service Architecture

### RAG Pipeline
```
User Query
  → Query Expansion (GPT-4o-mini)
  → Dense Search (OpenAI Embeddings + Qdrant)
  → Sparse Search (BM25)
  → Reciprocal Rank Fusion
  → Cross-Encoder Reranking
  → Context Enrichment
  → LLM Response (Streaming)
```

### Parser Pipeline
```
File Upload
  → File Type Detection
  → Parser (PDF/DOCX/PPTX/TXT/CSV)
  → OCR (PDF only, if text density < 100 chars/page)
  → Chunking (Recursive/Token/Markdown-aware)
  → Embedding (OpenAI or SentenceTransformer)
  → Vector Storage (Qdrant)
```

---

## Security

### Authentication
- Access tokens: 15min, stateless JWT
- Refresh tokens: 7 days, stateful (DB + Redis denylist)
- RTR (Refresh Token Rotation) with replay detection
- Bcrypt password hashing
- SHA-256 for refresh token comparison

### Rate Limiting
- Per-user request throttling
- Fail-open on Redis errors

### Path Security
- Storage downloads validate `startswith(base_path)` to block traversal

---

## Dependencies (Key Packages)

| Package | Purpose | Version |
|---------|---------|---------|
| fastapi | Web framework | Latest |
| sqlalchemy | ORM | 2.0.51 |
| asyncpg | PostgreSQL driver | Latest |
| redis | Redis client | Latest |
| qdrant-client | Vector DB | Latest |
| openai | LLM/Embeddings | Latest |
| pdfplumber | PDF parsing | Latest |
| python-docx | DOCX parsing | Latest |
| python-pptx | PPTX parsing | Latest |
| pypdfium2 | PDF rendering | Latest |
| pytesseract | OCR | Latest |
| celery | Task queue | Latest |
| starlette | ASGI framework | 0.41.3 |

---

## New Endpoints Added During Audit

### PATCH `/api/v1/documents/{id}` — Rename Document
**Purpose:** Allow users to rename uploaded documents  
**Request Body:** `{ "filename": "new_name.pdf" }`  
**Response:** Updated document metadata

### GET `/api/v1/documents/{id}/download` — Download Document
**Purpose:** Allow users to download original uploaded files  
**Response:** File content with proper `Content-Type` and `Content-Disposition` headers

---

## Known Limitations

1. **Celery:** Not running — document processing falls back to synchronous
2. **Missing Parsers:** XLSX, HTML, RTF not supported
3. **OCR Quality:** No pre-processing (deskew, contrast) before Tesseract
4. **No S3 Storage:** Only local filesystem storage implemented

---

## Recommendations

1. **Run Celery:** Deploy as Docker container or systemd service
2. **Add Parsers:** XLSX (openpyxl), HTML (BeautifulSoup), RTF
3. **OCR Enhancement:** Add pre-processing pipeline for better accuracy
4. **S3 Storage:** Implement S3StorageAdapter for production
5. **API Docs:** Publish OpenAPI spec for frontend code generation
6. **Monitoring:** Add Prometheus metrics endpoint

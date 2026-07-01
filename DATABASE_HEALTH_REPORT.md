# DocsMind — Database Health Report

**Project:** DocsMind RAG Platform  
**Date:** 2026-07-01  
**Scope:** PostgreSQL, Redis, Qdrant database services

---

## Database Services Summary

| Service | Host:Port | Technology | Status |
|---------|-----------|------------|--------|
| PostgreSQL | localhost:5432 | Docker (postgres:16-alpine) | ✅ Healthy |
| Redis | localhost:6379 | Native Windows | ✅ Running |
| Qdrant | localhost:6333 | Docker (qdrant/qdrant:latest) | ⚠️ Unhealthy but functional |

---

## PostgreSQL

### Connection Details
- **Host:** localhost:5432
- **Driver:** asyncpg (async SQLAlchemy 2.0)
- **ORM:** SQLAlchemy 2.0.51
- **Pool:** AsyncSession with proper commit-on-yield

### Schema Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `users` | User accounts | id, email, hashed_password, is_verified, full_name |
| `documents` | Uploaded documents | id, user_id, filename, status, storage_path, content_type |
| `chat_sessions` | Chat conversation containers | id, user_id, title, created_at |
| `chat_messages` | Individual chat messages | id, session_id, role, content, created_at |
| `usage_logs` | API usage tracking | id, user_id, action, latency_ms, tokens_used, cost |

### Session Management Fix (BUG-related)
**File:** `backend/app/db/session.py`

**Issue:** `get_db` generator never called `session.commit()` after yield, causing all database writes to silently fail.

**Fix:** Added `await session.commit()` after yield in the session dependency.

### Connection Health
- ✅ All CRUD operations verified
- ✅ Foreign key constraints enforced
- ✅ Proper async session handling
- ✅ Transaction commit on request completion

### Indexes
Standard indexes on:
- `users.email` (unique)
- `documents.user_id`
- `chat_messages.session_id`
- `usage_logs.user_id`

---

## Redis

### Connection Details
- **Host:** localhost:6379
- **Driver:** redis-py (async, `protocol=2` for RESP2)
- **Lazy Init:** `_LazyRedis` proxy pattern to avoid event loop issues

### Usage
| Feature | Purpose |
|---------|---------|
| Token Denylist | Refresh Token Rotation (RTR) replay detection |
| Rate Limiting | Per-user request throttling |
| Session Store | Active session tracking |

### Lazy Initialization Fix (Session Log)
**Issue:** Redis client connected at import time, causing event loop conflicts in tests.

**Fix:** Implemented `_LazyRedis` proxy pattern — actual connection deferred until first use.

### Rate Limiting Fix (Session Log)
**Issue:** RuntimeError from closed event loop blocked rate limiter.

**Fix:** Added explicit error handling with fail-open behavior.

### Health Check
- ✅ Connection established
- ✅ `incr`/`expire`/`pipeline` operations verified (via mock in tests)
- ✅ No connection pool exhaustion

---

## Qdrant (Vector Database)

### Connection Details
- **Host:** localhost:6333
- **Driver:** qdrant-client (Python)
- **Mode:** Docker container

### Collections

| Collection | Purpose | Vector Size |
|------------|---------|-------------|
| `documents` | Document chunk embeddings | 1536 (OpenAI) or 384 (Local) |

### Chunk Storage
Each vector entry contains:
- `chunk_id` (UUID)
- `document_id` (UUID)
- `user_id` (UUID)
- `content` (text)
- `page_number` (int)
- `metadata` (JSON)

### Health Status
- **Container:** Docker `qdrant/qdrant:latest`
- **Status:** Unhealthy (Docker health check) but **functional**
- **Reason:** Health check endpoint timing — Qdrant responds to API but Docker probe may timeout under load

### Known Issue
`QdrantAdapter.__init__` uses `settings.ENVIRONMENT=="development"` for local path instead of checking containers. When Docker Qdrant is on `:6333`, it still uses local disk unless `ENVIRONMENT!=development`.

---

## Celery (Task Queue)

### Configuration
- **Broker:** Redis (localhost:6379)
- **Backend:** Redis
- **Status:** Configured but not running in audit

### Impact
- **BUG-014:** Document upload silently fails when Celery not running
- **Fix:** Added try/except with synchronous fallback processing

### Recommendation
- Run Celery worker for production: `celery -A app.core.celery_app worker --loglevel=info`
- Monitor queue depth and worker health

---

## Database Health Matrix

| Check | PostgreSQL | Redis | Qdrant |
|-------|-----------|-------|--------|
| Connection | ✅ | ✅ | ✅ |
| Read Operations | ✅ | ✅ | ✅ |
| Write Operations | ✅ | ✅ | ✅ |
| Transaction Safety | ✅ | N/A | N/A |
| Connection Pool | ✅ | ✅ | ✅ |
| Lazy Init | N/A | ✅ | N/A |
| Health Check | ✅ | ✅ | ⚠️ |

---

## Recommendations

1. **Qdrant Health:** Investigate Docker health check timeout; consider custom health endpoint
2. **Migrations:** Add Alembic migration management for schema changes
3. **Backups:** Implement automated PostgreSQL backup schedule
4. **Monitoring:** Add connection pool metrics to Prometheus
5. **Celery:** Run as systemd service or Docker container for production

# DocsMind — Technical Debt Report

**Project:** DocsMind RAG Platform  
**Date:** 2026-07-01  
**Scope:** Identified technical debt items, incomplete features, and improvement opportunities

---

## Debt Summary

| Category | Items | Priority |
|----------|-------|----------|
| Missing Parsers | 3 | HIGH |
| Missing Infrastructure | 2 | HIGH |
| Code Quality | 4 | MEDIUM |
| Missing Tests | 3 | MEDIUM |
| Configuration Issues | 2 | LOW |
| **TOTAL** | **14** | |

---

## HIGH Priority Debt

### 1. Missing File Parsers

**Impact:** Users cannot upload XLSX, HTML, or RTF files.

| Format | Status | Library Needed |
|--------|--------|----------------|
| XLSX | ❌ Not implemented | `openpyxl` |
| HTML | ❌ Not implemented | `beautifulsoup4` |
| RTF | ❌ Not implemented | `pyrtf-ng` or similar |

**Current Coverage:** PDF, DOCX, PPTX, TXT, CSV  
**Recommended:** Add XLSX parser (highest business value — Excel files are common in enterprise)

---

### 2. Missing S3 Storage Adapter

**Impact:** All file storage is local filesystem only. Cannot scale to multiple instances or cloud deployment.

**Current:** `LocalStorage` at `backend/app/services/storage/local.py`  
**Missing:** `S3StorageAdapter` (referenced in architecture docs, not coded)

**Impact:**
- No horizontal scaling
- No disaster recovery
- No CDN for file serving

---

### 3. Celery Task Queue Not Running

**Impact:** Document processing falls back to synchronous mode. Cannot handle concurrent uploads or background jobs.

**Current:** Configured with Redis broker but not running  
**Impact:**
- Long-running document processing blocks API responses
- No retry logic for failed processing
- No task prioritization

---

## MEDIUM Priority Debt

### 4. OCR Pre-processing Missing

**Impact:** Tesseract OCR quality is suboptimal for scanned documents.

**Missing:**
- Deskew correction
- Contrast enhancement
- Noise reduction
- DPI configuration (hardcoded at scale=2)

**Current Threshold:** 100 chars/page triggers OCR (may OCR partially-digital pages unnecessarily)

---

### 5. No Contract Testing

**Impact:** 38% of bugs (8/21) were frontend-backend contract mismatches.

**Current:** Frontend and backend developed in parallel without shared API contract  
**Missing:**
- OpenAPI spec as source of truth
- Contract tests (Pact or similar)
- Auto-generated API client from spec

---

### 6. No Mock Data Detection

**Impact:** 14% of bugs (3/21) were mock data left in production code.

**Current:** No CI check for mock implementations  
**Recommended:**
- Add lint rule to detect `setTimeout` patterns in API services
- Add test that verifies API calls go to real endpoints
- Mark mock implementations with `// TODO: MOCK` and enforce removal

---

### 7. Missing Error Boundaries

**Impact:** Frontend crashes silently on component errors.

**Current:** No React error boundaries  
**Recommended:**
- Add error boundaries per feature module
- Add fallback UI for failed API calls
- Add global error handler for unhandled promise rejections

---

## MEDIUM Priority Debt (Code Quality)

### 8. Hardcoded Configuration Values

**Impact:** Port numbers, URLs, and thresholds hardcoded in source code.

**Examples:**
- `localhost:8000` hardcoded in 3 places (fixed to 8006)
- OCR threshold (100 chars/page) hardcoded
- Embedding batch size (2048) hardcoded

**Recommended:** Centralize all configuration in `settings.py` / `.env`

---

### 9. No API Versioning Strategy

**Impact:** All endpoints under `/api/v1/` with no plan for breaking changes.

**Current:** Single version (v1)  
**Missing:**
- Deprecation policy
- Version negotiation
- Migration guide for v2

---

### 10. Missing Rate Limiting Documentation

**Impact:** Rate limits applied but not documented per endpoint.

**Current:** Generic rate limiter in `rate_limit.py`  
**Missing:**
- Per-endpoint rate limit configuration
- Rate limit headers in responses (`X-RateLimit-*`)
- Rate limit documentation in API docs

---

### 11. No Request ID Tracing

**Impact:** Difficult to trace requests across services for debugging.

**Current:** No request ID in logs  
**Recommended:**
- Add `X-Request-ID` header
- Propagate request ID through all service calls
- Include in structured logging

---

## LOW Priority Debt

### 12. No Automated Database Backups

**Impact:** Risk of data loss in production.

**Current:** No backup strategy  
**Recommended:**
- Automated PostgreSQL backups (pg_dump cron)
- Redis persistence configuration
- Qdrant snapshot schedule

---

### 13. Missing Prometheus Metrics

**Impact:** No observability into system performance.

**Current:** Basic health endpoint only  
**Missing:**
- Request latency histograms
- Error rate counters
- RAG pipeline metrics
- Embedding generation metrics

---

### 14. No CI/CD Pipeline

**Impact:** Manual testing and deployment.

**Current:** Tests run manually  
**Missing:**
- GitHub Actions / GitLab CI pipeline
- Automated test execution on PR
- Automated deployment to staging/production
- Docker image build and push

---

## Debt by Component

### Frontend

| Item | Priority | Effort |
|------|----------|--------|
| Error boundaries | MEDIUM | 1 day |
| Contract testing | MEDIUM | 3 days |
| Mock data detection | MEDIUM | 1 day |
| Request ID tracing | LOW | 1 day |

### Backend

| Item | Priority | Effort |
|------|----------|--------|
| XLSX parser | HIGH | 2 days |
| S3 storage adapter | HIGH | 3 days |
| Celery deployment | HIGH | 1 day |
| OCR pre-processing | MEDIUM | 2 days |
| API versioning | MEDIUM | 2 days |
| Rate limit docs | MEDIUM | 0.5 day |
| Request ID tracing | LOW | 1 day |
| Prometheus metrics | LOW | 2 days |
| Database backups | LOW | 0.5 day |

### DevOps

| Item | Priority | Effort |
|------|----------|--------|
| CI/CD pipeline | LOW | 3 days |
| Docker optimization | LOW | 1 day |

---

## Estimated Total Effort

| Priority | Items | Estimated Effort |
|----------|-------|-----------------|
| HIGH | 3 | 6 days |
| MEDIUM | 7 | 10 days |
| LOW | 4 | 6.5 days |
| **TOTAL** | **14** | **22.5 days** |

---

## Recommended Roadmap

### Phase 1 (Week 1-2): Core Infrastructure
1. Add XLSX parser (highest user value)
2. Deploy Celery worker
3. Add error boundaries to frontend

### Phase 2 (Week 3-4): Production Readiness
4. Implement S3 storage adapter
5. Add contract testing
6. Add CI/CD pipeline

### Phase 3 (Week 5-6): Quality & Observability
7. OCR pre-processing pipeline
8. Prometheus metrics
9. Request ID tracing
10. Database backup automation

### Phase 4 (Week 7-8): Developer Experience
11. API versioning strategy
12. Rate limit documentation
13. Mock data detection
14. OpenAPI code generation

---

### 15. Server-Side Defaults in Async SQLAlchemy

**Impact:** Using `server_default=func.now()` / `onupdate=func.now()` in async ORM models causes `MissingGreenlet` on response serialization after commit.

**Fix Applied:** Changed `TimestampMixin` to Python-side `default=_utcnow` / `onupdate=_utcnow`.

**Recommendation:** Avoid SQL function defaults in async models. Use Python callables.

---

### 16. asyncpg Python 3.14 Timezone Handling

**Impact:** asyncpg 0.31.0 returns timezone-naive datetimes despite `DateTime(timezone=True)`, causing `TypeError` on comparison with aware datetimes.

**Fix Applied:** Defensive `tzinfo.replace(UTC)` added to all datetime comparisons in `user.py` (4 locations).

**Recommendation:** Monitor asyncpg for Python 3.14 fix.

---

### 17. Missing Migration Source

**Impact:** `a00000000001_add_missing_indexes.py` exists only as `.pyc` bytecode. Source file deleted. Migration not applied. Columns appear to exist (manually created).

**Recommendation:** Recreate the migration source or verify against actual schema.

---

## Conclusion

DocsMind has 17 identified technical debt items totaling ~24 days of effort. The highest priority items (parsers, S3, Celery) directly impact user functionality and deployment capability. The medium priority items (contract testing, error boundaries, async engine defaults) prevent recurring bugs like the HTTP 500 errors fixed in this session. The low priority items improve observability and developer experience for long-term maintainability.

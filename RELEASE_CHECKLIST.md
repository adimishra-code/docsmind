# v1.0.0-rc1 Release Checklist

## Pre-Release
- [x] All critical bugs fixed (9 bugs from initial audit)
- [x] Backend starts successfully (uvicorn on :8006)
- [x] Frontend builds successfully (tsc + vite, 4.68s)
- [x] Docker services start (PostgreSQL, Qdrant, Redis)
- [x] Alembic migrations apply cleanly
- [x] All API endpoints respond correctly (14 routes)
- [x] E2E workflow: register → login → upload → chat → analytics → logout
- [x] Refresh Token Rotation: replay protection verified

## Testing
- [x] pytest: 23/23 pass (1 skipped for optional dep)
- [x] vitest: 12/12 pass (including Storybook)
- [x] Security: auth, JWT, RTR, rate limiting, token type enforcement
- [x] Performance baselines recorded

## Documentation
- [x] README.md updated with quick-start guide
- [x] CLAUDE.md updated (stale bug list removed)
- [x] AGENTS.md already contains full session log
- [x] CHANGELOG.md created
- [x] .env ↔ docker-compose.dev.yml credentials aligned

## Release Artifacts
- [ ] Tag: `git tag -a v1.0.0-rc1 -m "v1.0.0 Release Candidate 1"`
- [ ] CI/CD pipeline (not yet configured — manual release)
- [ ] Publish Docker images (backend, frontend, worker)

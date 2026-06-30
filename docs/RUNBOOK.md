# Operational Runbook (Version 1.0)

This runbook provides actionable procedures for operating the DocsMind platform in production.

## 1. Deployment & Rollback

### Standard Deployment
Deployments are automated via GitHub Actions (see `.github/workflows/ci.yml`).
1. Merge PR to `main`.
2. Pipeline builds Docker images and pushes to the container registry.
3. CD pipeline triggers a rolling update on the cluster (e.g. ECS UpdateService).

### Emergency Rollback
If a deployment degrades the system (e.g., API returns 500s):
1. Identify the previous stable image tag (e.g., `docsmind-backend:v1.0.4`).
2. Revert the container orchestration manifest to target the old tag.
3. Force deployment.
*Note: If the bad deployment included a database migration (Alembic), you must manually run `alembic downgrade -1` before rolling back the code.*

## 2. Incident Response

### Scenario A: Celery Queue Backlog (Documents stuck in "Processing")
- **Symptom**: Users upload documents, but they never become searchable.
- **Diagnosis**: Check Redis memory and Celery worker logs. Likely a spike in large PDF uploads overwhelming the workers.
- **Resolution**: 
  1. Scale the `worker` service horizontally (e.g., increase ECS tasks from 2 to 10).
  2. Wait for the queue to drain.
  3. Scale back down.

### Scenario B: API Latency Spike (>3000ms)
- **Symptom**: Chat responses are timing out.
- **Diagnosis**: Check OpenAI API status. The LangGraph reasoner is likely blocking on external API limits or outages.
- **Resolution**: Update the configuration to point to a fallback LLM provider if configured, or post a banner to the frontend indicating degraded AI performance.

## 3. Log Management
- **Format**: All logs are emitted in JSON format via `structlog`.
- **Querying**: Logs are aggregated in CloudWatch/Datadog. 
  - To trace a specific request, filter by `"request_id"`.
  - To trace an entire user session, filter by `"user_id"`.

## 4. Maintenance Commands
- **Run Migrations**: `docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head`
- **Flush Redis (DANGER)**: `docker-compose -f docker-compose.prod.yml exec redis redis-cli flushall`

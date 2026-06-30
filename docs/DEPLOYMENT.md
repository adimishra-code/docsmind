# DocsMind Production Deployment Specification

DocsMind is deployed using Docker and Docker Compose for development and testing, and is prepared for container orchestration (Kubernetes) in production.

---

## 1. Container Topology

```
+---------------------------------------------------------------------------------+
|                               CONTAINER TOPOLOGY                                |
+-------------------+-------------------+-------------------+-----------------------+
| Service           | Port              | Role              | Scale Profile         |
+-------------------+-------------------+-------------------+-----------------------+
| Nginx             | 80 / 443          | API Gateway / SSL | N+1 Active-Active     |
+-------------------+-------------------+-------------------+-----------------------+
| FastAPI Backend   | 8000              | Web App / Routes  | Horizontal Autoscale  |
+-------------------+-------------------+-------------------+-----------------------+
| Celery Workers    | N/A               | Document Parsing  | Scaled by Queue Depth |
+-------------------+-------------------+-------------------+-----------------------+
| Redis             | 6379              | Cache / Broker    | Clustering Enabled    |
+-------------------+-------------------+-------------------+-----------------------+
| PostgreSQL        | 5432              | Core Database     | Master-Replica        |
+-------------------+-------------------+-------------------+-----------------------+
| Qdrant            | 6333 / 6334       | Vector Database   | Multi-node cluster    |
+-------------------+-------------------+-------------------+-----------------------+
```

---

## 2. Docker Compose (Development Configuration)

A typical local development orchestration structure is declared below:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: docsmind_db
    environment:
      POSTGRES_USER: docsmind
      POSTGRES_PASSWORD: docsmind_db_password
      POSTGRES_DB: docsmind
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    container_name: docsmind_redis
    command: redis-server --appendonly yes
    volumes:
      - redisdata:/data
    ports:
      - "6379:6379"

  qdrant:
    image: qdrant/qdrant:latest
    container_name: docsmind_vector
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrantdata:/qdrant/storage

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: docsmind_api
    environment:
      - ENVIRONMENT=development
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - qdrant

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: docsmind_worker
    command: celery -A app.workers.celery_app.celery worker --loglevel=info
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - redis
      - postgres

volumes:
  pgdata:
  redisdata:
  qdrantdata:
```
---

## 3. Production Scaling Rules
*   **Database connection pooling**: Deploy PgBouncer between FastAPI and PostgreSQL Master to reuse connections and reduce backend connection overhead.
*   **Ingestion autoscaling**: Set up Kubernetes Horizontal Pod Autoscaler (HPA) to scale the number of Celery worker pods dynamically based on the queue length (`celery_queue_depth` metric).
*   **Vector DB durability**: Run Qdrant in clustered mode with replication factor $\geq 2$ to prevent data loss.

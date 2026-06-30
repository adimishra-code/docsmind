# Release Notes - v1.0.0 "Enterprise Agentic AI"

We are thrilled to announce the Version 1.0 release of DocsMind. This marks the transition from a robust RAG prototype to a fully production-ready, highly observable Agentic AI Platform.

## 🌟 Major Highlights
- **LangGraph Multi-Agent System**: Replaced standard RAG with a powerful non-deterministic orchestrator (`Planner -> Retriever -> Reasoner -> Verifier -> Critic`).
- **Production DevOps**: Shipped multi-stage Dockerfiles and `docker-compose.prod.yml` enabling 1-click cloud deployments.
- **Enterprise Security**: Enforced zero-trust refresh token rotation (RTR), Nginx rate limiting, and prompt injection guards.
- **Agent Timeline UI**: The frontend now parses SSE agent execution events, visualizing the backend reasoning loop beautifully without overwhelming the user with raw data.

## 🚀 Features Ready for Production
- **Full-Text + Vector Hybrid Search**: Fusing BM25 and OpenAI Embeddings via Qdrant for maximum precision.
- **Cross-Encoder Reranking**: Reordering top results natively for semantic accuracy.
- **Asynchronous Document Parsing**: Offloading heavy OCR and PDF extraction to Celery workers backed by Redis.
- **Observability Suite**: JSON-structured logging (`structlog`), telemetry tracking (`UsageLog`), and deep metrics integration.

## 🛠️ Known Issues / Tech Debt
- Cross-encoder reranking currently blocks the event loop for ~400ms under heavy load. A future release will migrate this to a background GPU worker.
- BM25 indexes are currently recalculated on startup.

## 🔮 Roadmap (v1.1)
- Kubernetes native Helm charts.
- Azure OpenAI Fallback integration.
- RBAC (Role-Based Access Control) for enterprise teams.

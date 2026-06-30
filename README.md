# DocsMind

DocsMind is an Enterprise AI Document Intelligence Platform featuring a full RAG (Retrieval-Augmented Generation) pipeline managed by a multi-agent LangGraph system.

## Features
- **Hybrid Search**: Fused BM25 sparse vectors and OpenAI dense vectors via Qdrant.
- **Agentic AI**: Non-deterministic orchestrator for planning, retrieving, reasoning, and verifying knowledge.
- **Enterprise Ready**: Full Docker orchestration, stateless architecture, and secure JWT refresh token rotation.

## Deployment
Please refer to `docs/DEPLOYMENT_GUIDE.md` for full instructions on how to spin up the production cluster via Docker Compose.

## Architecture
See `docs/PLATFORM_ARCHITECTURE.md` for full service topology and request flows.

# DocsMind

Enterprise AI Document Intelligence Platform with a full RAG pipeline managed by a multi-agent LangGraph system.

## Quick Start

### Prerequisites
- Python 3.11+, Node.js 18+, Docker Desktop
- Tesseract OCR (for PDF parsing) — install via [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)

### 1. Clone & Configure
```bash
git clone https://github.com/your-org/docsmind.git
cd docsmind
cp backend/.env.example backend/.env
# Edit backend/.env — set OPENAI_API_KEY (optional for dev, mock key used by default)
```

### 2. Start Infrastructure (PostgreSQL, Qdrant, Redis)
```bash
docker compose -f docker-compose.dev.yml up -d postgres qdrant redis
```

### 3. Backend Setup
```bash
cd backend
pip install -r requirements.txt
# (Optional) pip install sentence-transformers torch transformers  # local embeddings/reranking
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8006 --reload
```

### 4. Frontend Setup
```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8006" > .env
npm run dev
```

### 5. Verify
```bash
curl http://localhost:8006/health
# {"status":"healthy","service":"DocsMind"}
```

## Running Tests
```bash
# Backend (24 tests, ~45s)
cd backend && python -m pytest tests/ -v

# Frontend (12 tests, ~15s)
cd frontend && npx vitest run src/
```

## Features
- **Hybrid Search**: Fused BM25 sparse vectors and OpenAI dense vectors via Qdrant.
- **Agentic AI**: Non-deterministic orchestrator for planning, retrieving, reasoning, and verifying knowledge.
- **Enterprise Ready**: Full Docker orchestration, stateless architecture, and secure JWT refresh token rotation.

## Deployment
See `docs/DEPLOYMENT_GUIDE.md` for production deployment via Docker Compose.

## Architecture
See `docs/PLATFORM_ARCHITECTURE.md` for full service topology and request flows.

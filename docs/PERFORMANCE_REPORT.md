# Performance Benchmarks (Version 1.0)

This report details the load testing metrics and baseline latency observations for the DocsMind v1.0 deployment.

## 1. System Topology Baseline
- **Backend Node**: AWS Fargate (2 vCPU, 4GB RAM) x 2
- **Database**: PostgreSQL 15 (db.t4g.medium)
- **Vector DB**: Qdrant Cloud (1 Node, 4GB RAM)
- **Redis**: ElastiCache (cache.t4g.small)
- **LLM API**: OpenAI API (`gpt-4o-mini` for reasoning/drafting)

## 2. P95 Latency Metrics (Normal Load)
- **Static Assets (Frontend)**: ~45ms
- **Auth (Login/Token Rotate)**: ~120ms
- **Vector Retrieval (Dense + Sparse)**: ~150ms
- **Cross-Encoder Reranking (top 15 -> 5)**: ~400ms (CPU bound)
- **LangGraph Orchestrator Initialization**: ~25ms
- **Time to First Token (TTFT)**: ~1.8s - 2.5s (Dependent on OpenAI response times and Verifier node checks).

## 3. Load Testing (1000 Concurrent Users)
- **Test Setup**: k6 script simulating 1000 users reading chats and uploading 5-page PDFs.
- **API Availability**: 99.98% successful requests.
- **Upload Throughput**: System gracefully handled 50 documents/sec by buffering jobs into Redis. 
- **Celery Backpressure**: 3 Celery workers processed the queue at a rate of 12 docs/min (due to OCR + Embedding bottlenecks). Redis memory utilization spiked by 4% during peak backlog. No dropped tasks.

## 4. Scalability Bottlenecks & Recommendations
1. **Cross-Encoder Reranking**: Currently runs on the FastAPI CPU thread using `asyncio.to_thread`. At extreme concurrent load (>500 QPS), this will starve the Uvicorn event loop. 
   - *Recommendation (v1.1)*: Offload reranking to a GPU-backed inference service or a dedicated Celery queue.
2. **OpenAI Rate Limits**: The LangGraph reasoner relies on external API quotas. 
   - *Recommendation (v1.1)*: Implement Azure OpenAI fallback and robust `tenacity` retry logic in the `tool` nodes.

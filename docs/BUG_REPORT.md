# Known Bugs & Technical Debt (v1.0)

While DocsMind v1.0 is certified for production, the following low-severity defects and technical debt items were recorded during the Phase 8 audit. They do not block deployment.

## 1. Backend Defects
- **[BUG-001] Cross-Encoder Event Loop Block**: The `CrossEncoderReranker` runs locally in the Python thread. Under extreme load, `asyncio.to_thread` still causes minor GIL contention. 
  - *Fix in v1.1*: Migrate to a dedicated inference server (e.g. Triton or vLLM) or push reranking to Celery.
- **[DEBT-001] BM25 Cold Start**: The sparse index relies on `rank-bm25` which keeps the corpus in RAM. If the backend restarts, it must fetch all text chunks from Postgres to rebuild the index.
  - *Fix in v1.1*: Implement a persistent BM25 index utilizing Qdrant's sparse vector capabilities (recently released).

## 2. Frontend Defects
- **[BUG-002] Long Citation Wrapping**: If a citation contains a single contiguous string (e.g., a massive base64 encoded image embedded in text), it breaks the flexbox layout in `CitationBadge.tsx`.
  - *Fix in v1.0.1*: Apply `break-words` and `truncate` to the citation text container.

## 3. LangGraph Limitations
- **[DEBT-002] Hardcoded Recursion Limits**: The `Critic` node can theoretically loop infinitely if it consistently fails. LangGraph defaults to a max recursion depth of 25, but we should explicitly set a hard cap at 3 retries.

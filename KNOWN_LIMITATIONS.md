# DocsMind v1.0 RC2 — Known Limitations

This document captures remaining architecture bottlenecks and non-blocking limitations in DocsMind Release Candidate 2.

## Summary of Limitations

### 1. Document Ingestion Fallbacks
- **Celery Connectivity**: If the Celery daemon is unreachable, the system falls back to a synchronous execution loop (`async_process_document` runs blocking loops). While functional for single uploads, large uploads will degrade uvicorn thread pool performance.
- **Parsing Format Coverage**: Parsers are configured for PDF, Word (DOCX), Text, CSV, and Presentation (PPTX) files. Document formats such as HTML, XLSX, and RTF are currently unsupported.

### 2. Retrieval and Search Cache
- **BM25 Sparse Indexing**: The sparse index is currently computed query-by-query or page-by-page. For high-volume production deployments, caching sparse indices in an external layer (e.g. Qdrant payload cache or separate Redis indexes) is recommended.

### 3. Agent Planning Stubs
- **LangGraph Flow Nodes**: The agent layout includes Critic and Composer nodes. Currently, these nodes serve as functional pass-through blocks rather than executing complex iteration loops.

### 4. Storage Adapter Setup
- **Storage Options**: Local filesystem storage adapter (`LocalStorage`) is fully supported. S3 / Cloud Storage adapters are designed but not fully implemented.

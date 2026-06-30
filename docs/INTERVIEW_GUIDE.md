# DocsMind Platform: System Design Interview Guide

This guide compiles advanced architectural questions, expected answers, and real-world trade-offs related to the platform's design.

---

## 1. System Design & Scaling

### Q1: How do you handle file uploads larger than 500MB without causing server memory exhaustion or blocking the event loop?
*   **Answer**: 
    1.  *Streaming Uploads*: Instead of loading the entire file into memory (FastAPI's default for small files), stream the file payload in chunks (e.g., 64KB) directly from the HTTP socket to a temporary directory on disk or upload directly to S3.
    2.  *Offloading Work*: The FastAPI endpoint validates the file metadata, generates a unique ID, saves the file location, and enqueues an ingestion task to Celery. The API immediately returns a `202 Accepted` response, freeing up the FastAPI worker process.
    3.  *Celery Worker Isolations*: The heavy lifting (parsing, OCR, chunking) is executed asynchronously inside dedicated Celery worker containers.

### Q2: What are the scaling bottlenecks when processing thousands of documents concurrently?
*   **Answer**:
    1.  *CPU Bottleneck (OCR/Parsing)*: OCR is highly CPU-bound. If workers run on the same VM as the web server, it degrades API responsiveness. *Solution*: Separate worker nodes and autoscale them based on Celery queue depth.
    2.  *Vector DB Write Limits*: Rebuilding HNSW indices during massive insertions is slow and memory-intensive. *Solution*: Disable index updates during batch imports, and trigger index rebuilds asynchronously once the batch import is complete.
    3.  *LLM API Rate Limits*: High-volume retrieval tasks quickly trigger rate limit errors (HTTP 429) from providers like OpenAI. *Solution*: Implement token-aware rate limiting at the worker level, implement exponential backoff retry policies, and configure a fallback provider (e.g., Anthropic Claude).

---

## 2. Machine Learning & RAG Engineering

### Q3: What is the semantic chunking trade-off, and why did you use Recursive Character chunking?
*   **Answer**:
    *   *Semantic Chunking* (splitting text based on embedding vector shifts between sentences) provides high retrieval accuracy by keeping semantic themes together. However, calculating similarity between every sentence requires many embedding API calls or high local CPU usage, making it slow and expensive.
    *   *Recursive Character Chunking* splits text based on a prioritized list of separators (e.g., paragraph breaks `\n\n`, line breaks `\n`, sentence endings, and spaces). It is fast, runs in $O(N)$ time locally, and preserves paragraph context. It serves as a robust default, with semantic chunking reserved as an opt-in setting for complex documents.

### Q4: Explain the difference between Dense Retrieval and Sparse Retrieval, and why they should be combined using RRF.
*   **Answer**:
    *   *Dense Retrieval* (Vector Search) captures semantic meaning and synonyms (e.g., matching "income statement" with "revenue breakdown"). However, it can miss exact serial numbers, product names, or acronyms.
    *   *Sparse Retrieval* (BM25 Keyword Search) matches exact tokens. It is highly effective for unique identifiers, product versions, or specific dates.
    *   *Reciprocal Rank Fusion (RRF)* combines the strengths of both approaches. By taking the reciprocal sum of their rank outputs, RRF yields a single, balanced relevance score without needing to normalize scores between the two search engines.

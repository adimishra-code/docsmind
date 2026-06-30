# Platform Architecture

DocsMind Version 1.0 is an enterprise-grade AI document intelligence platform designed for high availability, security, and scalability. This document details the infrastructure topology and request flows.

## 1. Service Diagram

```mermaid
graph TD
    Client[Web Client] -->|HTTPS| LB[Load Balancer / Nginx]
    LB -->|/api| Backend[FastAPI Backend]
    LB -->|/| Frontend[React Static Server]
    
    Backend -->|SQL| Postgres[(PostgreSQL)]
    Backend -->|Vectors| Qdrant[(Qdrant)]
    Backend -->|Cache/PubSub| Redis[(Redis)]
    
    Backend -->|Task Enqueue| Redis
    Redis -->|Dequeue| Celery[Celery Worker]
    Celery -->|SQL| Postgres
    Celery -->|Vectors| Qdrant
    
    Backend -->|API| LLM[OpenAI API]
    Celery -->|API| LLM
```

## 2. Request Flow (Streaming RAG)

```mermaid
sequenceDiagram
    participant User
    participant Nginx
    participant API as FastAPI (Chat)
    participant Retriever as HybridRetriever
    participant DB as Postgres/Qdrant
    participant LangGraph as Agent Orchestrator
    participant OpenAI
    
    User->>Nginx: POST /api/v1/chat (stream=true)
    Nginx->>API: Route Request
    API->>LangGraph: Initialize StateGraph
    LangGraph->>Retriever: Invoke Planner & Retriever Nodes
    Retriever->>DB: Dense + Sparse Query
    DB-->>Retriever: Top K Chunks
    LangGraph->>OpenAI: Invoke Reasoner Node
    OpenAI-->>LangGraph: Draft Output
    LangGraph->>LangGraph: Verifier & Critic Loop
    LangGraph-->>API: Yield SSE Events (agent_state, content)
    API-->>Nginx: Chunked Transfer
    Nginx-->>User: SSE Stream
```

## 3. Background Worker Flow (Document Ingestion)

```mermaid
sequenceDiagram
    participant API
    participant Redis
    participant Worker as Celery Worker
    participant Parser as PDF/Docx Parser
    participant Embedding as Embedding Model
    participant Qdrant
    
    API->>Redis: Delay upload_task(file_id)
    Redis->>Worker: Consume Task
    Worker->>Parser: Extract Text & Structure
    Parser-->>Worker: Raw Text
    Worker->>Worker: Chunking
    Worker->>Embedding: Generate Vectors
    Embedding-->>Worker: Vector Embeddings
    Worker->>Qdrant: Upsert Points
    Worker->>Redis: Mark Task Complete
```

## 4. Deployment Topology (Docker Compose)

```mermaid
graph LR
    subgraph DocsMind Production Stack
        Nginx[Nginx Reverse Proxy]
        Frontend[Frontend Container]
        API[FastAPI Container]
        Worker[Celery Worker Container]
        Scheduler[Celery Beat Container]
        
        subgraph Data Tier
            DB[(PostgreSQL)]
            Cache[(Redis)]
            VectorDB[(Qdrant)]
        end
    end
    
    Nginx --> API
    Nginx --> Frontend
    API --> DB
    API --> Cache
    API --> VectorDB
    Worker --> DB
    Worker --> Cache
    Worker --> VectorDB
```

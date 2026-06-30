# AI Evaluation & Observability Platform

## Overview
The AI Operations Console is the central hub for AI Engineers to evaluate, monitor, and debug the DocsMind system in production. It draws inspiration from industry-standard tools like LangSmith and Arize Phoenix to provide deep telemetry into RAG pipelines and LLM behaviors.

## Core Pillars
- **LLM Telemetry**: Tracks token consumption, latency percentiles, and hard costs over time (`LLMMetrics.tsx`).
- **Retrieval Analytics**: Visualizes vector database performance, plotting Recall@K, Context Precision, and chunk size distributions to tune chunking algorithms (`RetrievalMetrics.tsx`).
- **Hallucination Detection**: Tracks "Faithfulness" failures—instances where the LLM generated claims unsupported by the retrieved context chunks (`HallucinationTracker.tsx`).
- **Experimentation**: Allows engineers to compare the impact of different embedding models (e.g., `text-embedding-3-small` vs `bge-m3`) against a standardized evaluation dataset (`ExperimentTracker.tsx`).

## Architecture
- **Location**: `src/features/observability/components/`
- **Charting**: Utilizes `recharts` for robust, responsive data visualization.
- **State**: `useObservabilityStore` globally handles the active timeframe filters (24h, 7d, 30d) and selected models for comparison.
- **Data Hydration**: Currently relies on mock datasets injected at the `observabilityApi` SDK layer, designed to be swapped instantly once backend FastApi endpoints are exposed.

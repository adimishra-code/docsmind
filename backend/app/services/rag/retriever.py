from __future__ import annotations

import asyncio
from typing import Any
import uuid

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import get_logger
import app.db.session as db_session
from app.models.document import DocumentChunk
from app.services.rag.bm25_manager import BM25IndexManager
from app.services.rag.embeddings import get_embedding_provider
from app.services.rag.llm_client import get_llm_client
from app.services.rag.reranker import CrossEncoderReranker
from app.services.rag.sparse_search import SparseSearcher
from app.services.rag.vector_store import QdrantAdapter, VectorStoreInterface

logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# Reciprocal Rank Fusion (RRF) Implementation
# --------------------------------------------------------------------------- #
def reciprocal_rank_fusion(
    dense_results: list[dict[str, Any]],
    sparse_results: list[dict[str, Any]],
    k: int = 60,
) -> list[dict[str, Any]]:
    """Merges dense and sparse candidates using the Reciprocal Rank Fusion (RRF) formula."""
    rrf_scores: dict[uuid.UUID, float] = {}
    candidates: dict[uuid.UUID, dict[str, Any]] = {}

    def _accumulate_rrf(results: list[dict[str, Any]], source: str) -> None:
        for rank, res in enumerate(results, start=1):
            c_id = res["chunk_id"]
            # RRF score calculation: sum(1.0 / (k + rank))
            rrf_scores[c_id] = rrf_scores.get(c_id, 0.0) + (1.0 / (k + rank))
            
            if c_id not in candidates:
                candidates[c_id] = dict(res)
                candidates[c_id]["dense_or_sparse"] = source
            else:
                candidates[c_id]["dense_or_sparse"] = "hybrid"

    _accumulate_rrf(dense_results, "dense")
    _accumulate_rrf(sparse_results, "sparse")

    # Map scores back to candidate schemas
    fused_candidates = []
    for c_id, score in rrf_scores.items():
        cand = candidates[c_id]
        cand["score"] = score
        fused_candidates.append(cand)

    # Sort descending based on aggregated RRF rank
    fused_candidates.sort(key=lambda x: x["score"], reverse=True)
    return fused_candidates


# --------------------------------------------------------------------------- #
# Hybrid Retriever Orchestrator
# --------------------------------------------------------------------------- #
class HybridRetriever:
    """Enterprise-grade search aggregator implementing Dense, Sparse, RRF, and Reranking."""

    def __init__(self) -> None:
        from app.db.redis import redis_client
        self.embedding_provider = get_embedding_provider()
        self.vector_store: VectorStoreInterface = QdrantAdapter()
        self.index_manager = BM25IndexManager(redis_client)
        self.sparse_searcher = SparseSearcher(self.index_manager)
        self.reranker = CrossEncoderReranker()
        self.openai_client = get_llm_client()
        self.collection_name = "document_chunks"

    async def retrieve(
        self,
        query: str,
        user_id: uuid.UUID,
        *,
        limit: int = 5,
        document_ids: list[uuid.UUID] | None = None,
        multi_query: bool = False,
        expand_context: bool = False,
        rerank: bool = True,
    ) -> list[dict[str, Any]]:
        """Query RAG system, orchestrating fusion, expansions, and context extensions."""
        logger.info("Starting hybrid retrieval operation", query=query, user_id=user_id)

        # 1. Query Expansion (Multi-Query)
        queries = [query]
        if multi_query:
            expanded = await self._expand_query(query)
            queries.extend(expanded)
            logger.info("Query expanded into multiple variations", variations=queries)

        # 2. Gather retrieval runs concurrently
        dense_tasks = []
        sparse_tasks = []

        # Make sure the collection is ready in Qdrant (in-memory or remote)
        try:
            sample_vector = await self.embedding_provider.embed_query("test")
            vector_size = len(sample_vector)
        except Exception as exc:
            logger.warning("Failed to dynamically detect vector size. Falling back to default.", error=str(exc))
            vector_size = 1536
            if settings.EMBEDDING_PROVIDER != "openai":
                vector_size = 1024
        await self.vector_store.create_collection_if_not_exists(self.collection_name, vector_size)

        for q in queries:
            # Dense Lookup Task
            dense_tasks.append(self._retrieve_dense(q, user_id, limit * 2, document_ids))
            # Sparse Lookup Task
            sparse_tasks.append(self.sparse_searcher.search(q, user_id, limit=limit * 2, document_ids=document_ids))

        # Run search indexes in parallel
        dense_runs = await asyncio.gather(*dense_tasks)
        sparse_runs = await asyncio.gather(*sparse_tasks)

        # Flat map results
        all_dense: list[dict[str, Any]] = []
        all_sparse: list[dict[str, Any]] = []
        for run in dense_runs:
            all_dense.extend(run)
        for run in sparse_runs:
            all_sparse.extend(run)

        # Deduplicate results per run before fusion
        def _dedup_list(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            seen = set()
            deduped = []
            for item in items:
                c_id = item["chunk_id"]
                if c_id not in seen:
                    seen.add(c_id)
                    deduped.append(item)
            return deduped

        # 3. Apply Reciprocal Rank Fusion (RRF)
        fused = reciprocal_rank_fusion(_dedup_list(all_dense), _dedup_list(all_sparse))

        # 4. Cross-Encoder Reranking
        top_candidates = fused[: limit * 3]  # Feed top candidates into reranker
        if rerank:
            ranked = await self.reranker.rerank(query, top_candidates)
        else:
            # Fallback score copy
            ranked = top_candidates
            for item in ranked:
                item["rerank_score"] = item["score"]

        # Slice to final Top-K
        final_candidates = ranked[:limit]

        # 5. Parent-Child Adjacent Context Enrichment
        if expand_context:
            final_candidates = await self._enrich_with_adjacent_chunks(final_candidates)

        return final_candidates

    async def _retrieve_dense(
        self,
        query: str,
        user_id: uuid.UUID,
        limit: int,
        document_ids: list[uuid.UUID] | None,
    ) -> list[dict[str, Any]]:
        """Helper to generate query vector and search Qdrant."""
        try:
            query_vector = await self.embedding_provider.embed_query(query)
            return await self.vector_store.search_chunks(
                self.collection_name,
                query_vector,
                user_id,
                limit=limit,
                document_ids=document_ids,
            )
        except Exception as exc:
            logger.error("Dense retrieval lookup failed. Returning empty.", error=str(exc))
            return []

    async def _expand_query(self, original_query: str) -> list[str]:
        """Generate alternative search query formulations using the LLM."""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AI assistant designed to expand search queries for a document retrieval engine. "
                            "Generate exactly 3 alternative search queries that represent semantic variations of the user input. "
                            "Keep queries concise and separate each by a newline. Do not output numbers, explanations, or quotes."
                        ),
                    },
                    {"role": "user", "content": original_query},
                ],
                temperature=0.3,
                max_tokens=150,
            )
            content = response.choices[0].message.content or ""
            return [line.strip() for line in content.splitlines() if line.strip()]
        except Exception as exc:
            logger.warn("Query expansion failed. Proceeding with original query only.", error=str(exc))
            return []

    async def _enrich_with_adjacent_chunks(
        self,
        candidates: list[dict[str, Any]],
        radius: int = 1,
    ) -> list[dict[str, Any]]:
        """Fetch surrounding chunk nodes (N-radius to N+radius) from relational database in a single batched query to expand context."""
        logger.info("Enriching candidates with adjacent database chunks", batch_size=len(candidates))
        
        if not candidates:
            return []

        doc_indices = {}  # doc_id -> set of target chunk indices
        
        for cand in candidates:
            doc_id = uuid.UUID(cand["payload"]["document_id"])
            idx = cand["payload"]["chunk_index"]
            if doc_id not in doc_indices:
                doc_indices[doc_id] = set()
            for i in range(idx - radius, idx + radius + 1):
                if i >= 0:
                    doc_indices[doc_id].add(i)

        if not doc_indices:
            return candidates

        async with db_session.AsyncSessionLocal() as session:
            from sqlalchemy import or_
            or_clauses = []
            for doc_id, indices in doc_indices.items():
                or_clauses.append(
                    (DocumentChunk.document_id == doc_id) & (DocumentChunk.chunk_index.in_(indices))
                )
            
            stmt = select(DocumentChunk).where(or_(*or_clauses))
            res = await session.execute(stmt)
            nodes = res.scalars().all()

        chunk_map: dict[str, dict[int, str]] = {}
        for node in nodes:
            did = str(node.document_id)
            if did not in chunk_map:
                chunk_map[did] = {}
            chunk_map[did][node.chunk_index] = node.content

        enriched_candidates = []
        for cand in candidates:
            doc_id_str = cand["payload"]["document_id"]
            idx = cand["payload"]["chunk_index"]
            
            doc_map = chunk_map.get(doc_id_str, {})
            
            window_texts = []
            for i in range(idx - radius, idx + radius + 1):
                if i in doc_map:
                    window_texts.append(doc_map[i])

            if window_texts:
                expanded_text = "\n\n... [Adjacent Context] ...\n\n".join(window_texts)
                updated_cand = dict(cand)
                updated_cand["payload"] = dict(cand["payload"])
                updated_cand["payload"]["content"] = expanded_text
                updated_cand["payload"]["original_content"] = cand["payload"]["content"]
                enriched_candidates.append(updated_cand)
            else:
                enriched_candidates.append(cand)

        return enriched_candidates

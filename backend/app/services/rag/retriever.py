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


def _debug_chunk(cand: dict[str, Any]) -> dict[str, Any]:
    """Compact, log-safe view of a retrieved chunk for dev-only tracing."""
    payload = cand.get("payload") or {}
    snippet = (payload.get("content") or "")[:80].replace("\n", " ")
    rerank = cand.get("rerank_score")
    return {
        "doc": payload.get("filename") or payload.get("document_id"),
        "page": payload.get("page_number"),
        "idx": payload.get("chunk_index"),
        "rerank": round(rerank, 4) if isinstance(rerank, (int, float)) else None,
        "score": round(cand.get("score", 0.0), 4),
        "text": snippet,
    }


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
        top_candidates = fused[: limit * 5]  # Feed top candidates into reranker
        if rerank:
            ranked = await self.reranker.rerank(query, top_candidates)
        else:
            # Fallback score copy
            ranked = top_candidates
            for item in ranked:
                item["rerank_score"] = item["score"]

        # 5. Take the most relevant chunks by rerank score.
        #
        # We deliberately do NOT apply cross-document "diversity" here. For a
        # single, focused question that logic forcibly injects chunks from
        # UNRELATED documents to promote breadth, evicting the lower-ranked
        # chunks of the document that actually answers the query. That was the
        # real cause of "projects of Aditya Mishra -> not found" while the
        # context filled with EPROM/PROM/Mughal chunks and a CV header chunk was
        # still (correctly) cited. Breadth for genuinely multi-topic questions is
        # handled upstream by query decomposition + merge_runs(), which balances
        # across the results of each sub-question — so single-query retrieval
        # should simply maximize relevance.
        final_candidates = ranked[:limit]

        if settings.DEBUG:
            logger.debug(
                "retrieval.trace",
                query=query,
                dense=len(all_dense),
                sparse=len(all_sparse),
                fused=len(fused),
                reranked=[_debug_chunk(c) for c in ranked[: limit * 2]],
                final=[_debug_chunk(c) for c in final_candidates],
            )

        # 6. Parent-Child Adjacent Context Enrichment
        if expand_context:
            final_candidates = await self._enrich_with_adjacent_chunks(final_candidates)

        return final_candidates

    @staticmethod
    def merge_runs(
        runs: list[list[dict[str, Any]]],
        total_limit: int,
    ) -> list[dict[str, Any]]:
        """Merge the retrieval results of several sub-questions into one context.

        Steps (context optimization):
        1. De-duplicate by chunk_id, keeping each chunk's best (max) score so a
           chunk found by two sub-questions is counted once, not twice.
        2. Rank by score, then apply cross-document diversity so the final
           context is balanced across every relevant document (no single PDF
           consuming the whole window).
        3. Re-order the survivors by (document, chunk_index) so chunks from the
           same source arrive in their natural reading order — denser, more
           coherent context for the LLM.
        """
        best: dict[Any, dict[str, Any]] = {}
        for run in runs:
            for item in run:
                c_id = item["chunk_id"]
                prior = best.get(c_id)
                score = item.get("rerank_score") or item.get("score") or 0.0
                if prior is None or score > (prior.get("rerank_score") or prior.get("score") or 0.0):
                    best[c_id] = item

        ranked = sorted(
            best.values(),
            key=lambda x: x.get("rerank_score") or x.get("score") or 0.0,
            reverse=True,
        )
        balanced = HybridRetriever._diversify_by_document(ranked, total_limit)

        def _sort_key(cand: dict[str, Any]) -> tuple[str, int]:
            payload = cand.get("payload") or {}
            return (payload.get("document_id", ""), payload.get("chunk_index", 0))

        return sorted(balanced, key=_sort_key)

    @staticmethod
    def _diversify_by_document(
        ranked: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Select the final Top-K, balancing cross-document breadth against
        relevance so neither concern starves the other.

        Two passes:
        1. **Guarantee relevance** — the top ``limit // 2`` chunks by pure
           relevance are always kept. This is the safety net for questions that
           are genuinely about ONE document (e.g. "the projects in Aditya's CV"):
           the dominant document's most-relevant chunks — the very section that
           answers the question — must never be dropped to make room for weakly
           relevant chunks from other documents.
        2. **Diversify the rest** — remaining slots prefer under-represented
           documents (capped per document) so multi-document questions still span
           the workspace, then any leftover slots are filled by relevance.

        Single-document questions are unaffected (everything comes from one doc).
        """
        if limit <= 0 or not ranked:
            return ranked[:limit]

        def _doc_of(cand: dict[str, Any]) -> str:
            return (cand.get("payload") or {}).get("document_id", "")

        # Pass 1 — keep the most-relevant half no matter which documents they
        # come from, so a dominant, clearly-on-topic document is never starved.
        guaranteed = max(1, limit // 2)
        selected: list[dict[str, Any]] = list(ranked[:guaranteed])
        per_doc: dict[str, int] = {}
        for cand in selected:
            per_doc[_doc_of(cand)] = per_doc.get(_doc_of(cand), 0) + 1

        # A single document may fill at most this many of the final slots — high
        # enough that a dominant document keeps the relevant chunks it earned,
        # low enough that it can't consume the entire context window.
        max_per_doc = max(guaranteed, (limit + 2) // 3)

        # Pass 2 — fill the rest, preferring documents below their cap.
        deferred: list[dict[str, Any]] = []
        for cand in ranked[guaranteed:]:
            if len(selected) >= limit:
                break
            doc = _doc_of(cand)
            if per_doc.get(doc, 0) < max_per_doc:
                selected.append(cand)
                per_doc[doc] = per_doc.get(doc, 0) + 1
            else:
                deferred.append(cand)

        # Backfill any unfilled slots with the highest-relevance leftovers.
        if len(selected) < limit:
            selected.extend(deferred[: limit - len(selected)])

        return selected

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
        """Generate alternative search query formulations using the LLM.

        Routed through the pluggable provider abstraction (get_llm_provider) so
        it works with local/Ollama models and never hard-requires OpenAI. Any
        failure is non-fatal: we degrade to the original query alone.
        """
        prompt = (
            "You expand search queries for a document retrieval engine. Generate exactly 3 "
            "alternative search queries that capture semantic variations of the user input, "
            "each on its own line. Output only the queries — no numbering, quotes, or explanations.\n\n"
            f"User query: {original_query}"
        )
        try:
            from app.services.rag.llm_provider import get_llm_provider

            content = await get_llm_provider().ainvoke(prompt, temperature=0.3)
            variations = [line.strip("-•* \t") for line in content.splitlines() if line.strip()]
            # Guard against a model that echoes the prompt or returns the original.
            return [v for v in variations if v and v.lower() != original_query.lower()][:3]
        except Exception as exc:
            logger.warning("Query expansion failed. Proceeding with original query only.", error=str(exc))
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

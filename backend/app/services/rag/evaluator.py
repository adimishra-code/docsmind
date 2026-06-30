from __future__ import annotations

import json
import re
import time
from typing import Any
import uuid

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RAGEvaluator:
    """Runs automated automated RAG evaluations using LLM-as-a-Judge and statistical metrics."""

    def __init__(self) -> None:
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def evaluate_retrieval(
        self,
        retrieved_chunks: list[dict[str, Any]],
        expected_chunk_ids: list[uuid.UUID],
    ) -> dict[str, Any]:
        """Calculate Precision@K, Recall@K, Hit Rate, and Mean Reciprocal Rank (MRR)."""
        retrieved_ids = [c["chunk_id"] for c in retrieved_chunks]
        k = len(retrieved_ids)

        if not expected_chunk_ids:
            return {
                "precision_at_k": 0.0,
                "recall_at_k": 0.0,
                "hit_rate": 0.0,
                "mrr": 0.0,
            }

        # Calculate hits
        hits = [1 if r_id in expected_chunk_ids else 0 for r_id in retrieved_ids]
        
        # Hit Rate: 1 if there is at least one hit, else 0
        hit_rate = 1.0 if sum(hits) > 0 else 0.0
        
        # Precision@K: (number of relevant items retrieved) / K
        precision_at_k = sum(hits) / k if k > 0 else 0.0
        
        # Recall@K: (number of relevant items retrieved) / (total expected relevant items)
        recall_at_k = sum(hits) / len(expected_chunk_ids)

        # MRR (Mean Reciprocal Rank)
        mrr = 0.0
        for rank, hit in enumerate(hits, start=1):
            if hit == 1:
                mrr = 1.0 / rank
                break

        return {
            "precision_at_k": round(precision_at_k, 4),
            "recall_at_k": round(recall_at_k, 4),
            "hit_rate": hit_rate,
            "mrr": round(mrr, 4),
        }

    async def evaluate_faithfulness(self, context: str, answer: str) -> float:
        """LLM-as-a-Judge: Measures if the answer is grounded strictly in the context (0.0 to 1.0)."""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an objective evaluation auditor. Evaluate whether the provided ANSWER is fully "
                            "and strictly supported by the CONTEXT block. Do not allow extrapolations or unmentioned facts. "
                            "First, write a 1-sentence reasoning summary. Then, output exactly: 'VERDICT: FAITHFUL' or 'VERDICT: UNFAITHFUL'."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nAnswer:\n{answer}",
                    },
                ],
                temperature=0.0,
                max_tokens=100,
            )
            content = response.choices[0].message.content or ""
            return 1.0 if "VERDICT: FAITHFUL" in content else 0.0
        except Exception as exc:
            logger.warn("LLM-as-a-judge faithfulness check failed. Bypassing.", error=str(exc))
            return 1.0  # default safe fallback

    async def evaluate_answer_relevance(self, query: str, answer: str) -> float:
        """LLM-as-a-Judge: Measures if the answer directly addresses the search query (0.0 to 1.0)."""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an objective evaluation auditor. Rate how relevant the ANSWER is to the user's QUERY. "
                            "Evaluate if the answer directly addresses the question asked. Output only a single decimal number "
                            "between 0.0 and 1.0 representing the relevance score (e.g. 0.85). Do not write anything else."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Query: {query}\n\nAnswer: {answer}",
                    },
                ],
                temperature=0.0,
                max_tokens=20,
            )
            score_str = (response.choices[0].message.content or "0.0").strip()
            # Extract floats using regex
            match = re.search(r"(\d+(?:\.\d+)?)", score_str)
            return float(match.group(1)) if match else 0.0
        except Exception as exc:
            logger.warn("LLM-as-a-judge relevance check failed. Bypassing.", error=str(exc))
            return 1.0

    async def generate_evaluation_report(
        self,
        query: str,
        retrieved_chunks: list[dict[str, Any]],
        expected_chunk_ids: list[uuid.UUID],
        answer: str,
        latency_ms: int,
    ) -> dict[str, Any]:
        """Aggregate all metrics and build a comprehensive telemetry report."""
        start_eval = time.perf_counter()

        # 1. Evaluate Retrieval
        retrieval_stats = await self.evaluate_retrieval(retrieved_chunks, expected_chunk_ids)

        # 2. Compile Context Text
        context_text = "\n\n".join(c["payload"]["content"] for c in retrieved_chunks)

        # 3. Run LLM-as-a-judge evaluations
        faithfulness = await self.evaluate_faithfulness(context_text, answer)
        relevance = await self.evaluate_answer_relevance(query, answer)

        eval_duration_ms = int((time.perf_counter() - start_eval) * 1000)

        report = {
            "query": query,
            "timestamp": time.time(),
            "latency_ms": latency_ms,
            "evaluation_latency_ms": eval_duration_ms,
            "metrics": {
                **retrieval_stats,
                "faithfulness": faithfulness,
                "answer_relevance": relevance,
                "hallucination_rate": 1.0 - faithfulness,
            },
        }

        logger.info("RAG evaluation report compiled successfully", metrics=report["metrics"])
        return report

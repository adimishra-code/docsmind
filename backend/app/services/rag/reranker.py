from __future__ import annotations

import asyncio
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CrossEncoderReranker:
    """Re-ranks retrieved candidates utilizing CrossEncoder semantic similarity models."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.RERANK_MODEL
        logger.info("Initializing CrossEncoder reranker", model=self.model_name)
        self._model: Any = None

    @property
    def model(self) -> Any:
        if self._model is None:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name)
        return self._model

    async def rerank(self, query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Compute Cross-Encoder scores for query-passage pairs and reorder them."""
        if not candidates:
            return []

        logger.info("Reranking candidate chunks", count=len(candidates), query=query)

        # Create input pairs [(query, passage)] for the model
        pairs = [(query, cand["payload"]["content"]) for cand in candidates]

        # Execute CPU/GPU inference in a separate thread pool to prevent event loop delay
        scores = await asyncio.to_thread(self._predict_sync, pairs)

        # Map scores to candidate dictionaries
        reranked_list = []
        for cand, score in zip(candidates, scores, strict=True):
            # Deep copy or construct a new dict to preserve clean metadata state
            updated_cand = dict(cand)
            updated_cand["rerank_score"] = float(score)
            # Retain original search engine details for evaluation telemetry
            updated_cand["telemetry"] = {
                "dense_or_sparse": cand.get("dense_or_sparse", "unknown"),
                "original_score": cand["score"],
            }
            reranked_list.append(updated_cand)

        # Sort candidates descending based on Cross-Encoder relevance logits
        reranked_list.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked_list

    def _predict_sync(self, pairs: list[tuple[str, str]]) -> Any:
        return self.model.predict(pairs)

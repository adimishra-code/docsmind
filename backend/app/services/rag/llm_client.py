"""Shared LLM client singleton for OpenAI API calls."""
from __future__ import annotations

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_llm_client: AsyncOpenAI | None = None


def get_llm_client() -> AsyncOpenAI:
    global _llm_client
    if _llm_client is None:
        logger.info("Creating shared AsyncOpenAI client")
        kwargs = {"api_key": settings.OPENAI_API_KEY}
        if settings.LLM_BASE_URL:
            kwargs["base_url"] = settings.LLM_BASE_URL
        _llm_client = AsyncOpenAI(**kwargs)
    return _llm_client


def reset_llm_client() -> None:
    global _llm_client
    _llm_client = None
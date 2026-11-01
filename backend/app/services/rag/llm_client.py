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
        api_key = settings.LLM_API_KEY or settings.OPENAI_API_KEY
        kwargs: dict = {"api_key": api_key}
        base_url = settings.LLM_BASE_URL
        if not base_url and settings.LLM_PROVIDER.lower().strip() == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
        if base_url:
            kwargs["base_url"] = base_url
            if "openrouter.ai" in base_url:
                kwargs["default_headers"] = {
                    "HTTP-Referer": "https://docsmind.app",
                    "X-Title": "DocsMind",
                    "Authorization": f"Bearer {api_key}",
                }
        _llm_client = AsyncOpenAI(**kwargs)
    return _llm_client


def reset_llm_client() -> None:
    global _llm_client
    _llm_client = None
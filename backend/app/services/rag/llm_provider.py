"""Pluggable LLM providers for the RAG agent graph.

This is the single execution path for text generation across every LangGraph
node (planner, reasoner, critic, composer). It mirrors the embedding-provider
pattern in ``embeddings.py`` so the chat pipeline is:

    ChatService -> agent nodes -> get_llm_provider() -> configured provider -> stream

OpenAI is one *optional* provider, not a hard dependency. DocsMind runs with **no
OpenAI key** by pointing ``LLM_PROVIDER`` at either:

* ``ollama`` (or any OpenAI-compatible server via ``LLM_BASE_URL`` — vLLM, LM
  Studio, LocalAI). Local servers ignore auth, so no key is required.
* ``local`` — fully in-process generation with HuggingFace ``transformers``.

The OpenAI-compatible provider keeps ``langchain_openai.ChatOpenAI`` under the
hood so it works identically whether it talks to api.openai.com or a local
Ollama endpoint.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from app.core.config import INSECURE_OPENAI_KEY, settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Default endpoint for a local Ollama server exposing the OpenAI-compatible API.
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"


class BaseLLMProvider(ABC):
    """Interface every LLM provider must implement.

    Both methods accept a single prompt string (the agent nodes build fully
    rendered prompts) and a per-call ``temperature`` so different nodes can tune
    determinism without constructing their own clients.
    """

    @abstractmethod
    async def ainvoke(self, prompt: str, *, temperature: float = 0.0) -> str:
        """Return the full completion for ``prompt``."""

    @abstractmethod
    def astream(self, prompt: str, *, temperature: float = 0.0) -> AsyncIterator[str]:
        """Yield completion text incrementally as it is generated."""


class OpenAICompatLLMProvider(BaseLLMProvider):
    """Talks to OpenAI or any OpenAI-compatible endpoint via ``LLM_BASE_URL``.

    When a ``base_url`` is configured (e.g. a local Ollama/vLLM server) the API
    key is optional; we fall back to a non-empty sentinel because the OpenAI SDK
    refuses to construct a client with an empty key even though local servers
    ignore it.
    """

    def __init__(self, *, base_url: str | None = None, require_key: bool = False) -> None:
        # Imported lazily so importing this module never hard-requires
        # langchain_openai (keeps the local provider path dependency-light).
        from langchain_openai import ChatOpenAI

        self._ChatOpenAI = ChatOpenAI
        self.model = settings.LLM_MODEL
        self.base_url = base_url if base_url is not None else settings.LLM_BASE_URL

        configured_key = settings.LLM_API_KEY or settings.OPENAI_API_KEY
        key_is_placeholder = not configured_key or configured_key == INSECURE_OPENAI_KEY
        if require_key and key_is_placeholder and settings.is_production:
            # In production, talking to real OpenAI with no real key: fail loudly
            # and honestly rather than emitting a confusing 401 mid-stream. Dev
            # and test tolerate the placeholder (calls are mocked / local).
            raise LLMConfigurationError(
                "LLM_PROVIDER=openai targets the OpenAI API but no valid OPENAI_API_KEY "
                "is set. Provide a key, or set LLM_PROVIDER=ollama / LLM_PROVIDER=local "
                "to run without OpenAI."
            )
        # Local/compatible servers ignore auth; keep a non-empty sentinel.
        self.api_key = configured_key or "not-needed"

    def _client(self, temperature: float):
        kwargs: dict = {"model": self.model, "api_key": self.api_key, "temperature": temperature}
        if self.base_url:
            kwargs["base_url"] = self.base_url
            if "openrouter.ai" in self.base_url:
                kwargs["default_headers"] = {
                    "HTTP-Referer": "https://docsmind.app",
                    "X-Title": "DocsMind",
                    "Authorization": f"Bearer {self.api_key}",
                }
        return self._ChatOpenAI(**kwargs)

    async def ainvoke(self, prompt: str, *, temperature: float = 0.0) -> str:
        response = await self._client(temperature).ainvoke(prompt)
        return response.content or ""

    async def astream(self, prompt: str, *, temperature: float = 0.0) -> AsyncIterator[str]:
        async for chunk in self._client(temperature).astream(prompt):
            if chunk.content:
                yield chunk.content


class LocalTransformersLLMProvider(BaseLLMProvider):
    """Fully local, in-process generation via HuggingFace ``transformers``.

    No network, no API key. Heavier at runtime (model weights are downloaded on
    first use and held in memory) but keeps DocsMind functional with zero
    external LLM services. The model is loaded lazily so importing/constructing
    the provider is cheap.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.LOCAL_LLM_MODEL
        self._pipe = None

    def _pipeline(self):
        if self._pipe is None:
            try:
                from transformers import pipeline
            except ImportError as exc:  # pragma: no cover - env-dependent
                raise LLMConfigurationError(
                    "LLM_PROVIDER=local requires the 'transformers' package to be installed."
                ) from exc
            logger.info("Loading local text-generation model", model=self.model_name)
            self._pipe = pipeline("text-generation", model=self.model_name)
        return self._pipe

    async def ainvoke(self, prompt: str, *, temperature: float = 0.0) -> str:
        import asyncio

        def _generate() -> str:
            pipe = self._pipeline()
            do_sample = temperature > 0.0
            out = pipe(
                prompt,
                max_new_tokens=512,
                do_sample=do_sample,
                temperature=temperature if do_sample else None,
                return_full_text=False,
            )
            return out[0]["generated_text"] if out else ""

        return await asyncio.to_thread(_generate)

    async def astream(self, prompt: str, *, temperature: float = 0.0) -> AsyncIterator[str]:
        import asyncio

        pipe = self._pipeline()
        try:
            from transformers import TextIteratorStreamer
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise LLMConfigurationError(
                "LLM_PROVIDER=local requires the 'transformers' package to be installed."
            ) from exc

        streamer = TextIteratorStreamer(
            pipe.tokenizer, skip_prompt=True, skip_special_tokens=True
        )
        do_sample = temperature > 0.0
        generation_kwargs = dict(
            text_inputs=prompt,
            max_new_tokens=512,
            do_sample=do_sample,
            temperature=temperature if do_sample else None,
            streamer=streamer,
            return_full_text=False,
        )

        loop = asyncio.get_running_loop()
        task = loop.run_in_executor(None, lambda: pipe(**generation_kwargs))
        for token in streamer:  # yields incrementally as generation proceeds
            if token:
                yield token
        await task


class LLMConfigurationError(RuntimeError):
    """Raised when the configured LLM provider cannot be constructed/used."""


def get_llm_provider() -> BaseLLMProvider:
    """Return the provider selected by ``settings.LLM_PROVIDER``.

    * ``openai`` — real OpenAI (requires a key) or any OpenAI-compatible server
      when ``LLM_BASE_URL`` is set.
    * ``ollama`` — local Ollama (or compatible) server; no key required.
    * ``local`` — in-process transformers generation; no key, no network.
    """
    provider = settings.LLM_PROVIDER.lower().strip()

    if provider == "openai":
        # Only demand a real key when actually pointing at hosted OpenAI.
        return OpenAICompatLLMProvider(require_key=settings.LLM_BASE_URL is None)
    if provider == "openrouter":
        base_url = settings.LLM_BASE_URL or "https://openrouter.ai/api/v1"
        return OpenAICompatLLMProvider(base_url=base_url, require_key=True)
    if provider == "ollama":
        base_url = settings.LLM_BASE_URL or DEFAULT_OLLAMA_BASE_URL
        return OpenAICompatLLMProvider(base_url=base_url, require_key=False)
    if provider in ("local", "transformers", "huggingface"):
        return LocalTransformersLLMProvider()

    logger.error("Unknown LLM provider configured. Falling back to OpenAI-compatible.", provider=provider)
    return OpenAICompatLLMProvider(require_key=settings.LLM_BASE_URL is None)

"""Unit tests for the pluggable LLM provider layer.

These assert that DocsMind can select an execution path WITHOUT an OpenAI key
(the whole point of the abstraction) and that the factory maps config to the
right provider.
"""
from __future__ import annotations

import pytest

import app.core.config as config_module
from app.services.rag import llm_provider
from app.services.rag.llm_provider import (
    BaseLLMProvider,
    LocalTransformersLLMProvider,
    OpenAICompatLLMProvider,
    get_llm_provider,
)


def _set(monkeypatch, **kwargs) -> None:
    for key, value in kwargs.items():
        monkeypatch.setattr(config_module.settings, key, value, raising=False)


def test_factory_openai_default(monkeypatch) -> None:
    _set(monkeypatch, LLM_PROVIDER="openai", LLM_BASE_URL=None, ENVIRONMENT="development")
    provider = get_llm_provider()
    assert isinstance(provider, OpenAICompatLLMProvider)
    assert isinstance(provider, BaseLLMProvider)


def test_factory_ollama_needs_no_key(monkeypatch) -> None:
    # No OpenAI key present, provider=ollama -> must still construct cleanly and
    # default to the local Ollama endpoint.
    _set(monkeypatch, LLM_PROVIDER="ollama", LLM_BASE_URL=None, OPENAI_API_KEY="", LLM_API_KEY=None)
    provider = get_llm_provider()
    assert isinstance(provider, OpenAICompatLLMProvider)
    assert provider.base_url == llm_provider.DEFAULT_OLLAMA_BASE_URL
    assert provider.api_key  # non-empty sentinel so the SDK constructs


def test_factory_local(monkeypatch) -> None:
    _set(monkeypatch, LLM_PROVIDER="local")
    provider = get_llm_provider()
    assert isinstance(provider, LocalTransformersLLMProvider)


def test_factory_unknown_falls_back(monkeypatch) -> None:
    _set(monkeypatch, LLM_PROVIDER="does-not-exist", LLM_BASE_URL=None)
    provider = get_llm_provider()
    assert isinstance(provider, OpenAICompatLLMProvider)


def test_openai_provider_hard_fails_only_in_production(monkeypatch) -> None:
    from app.services.rag.llm_provider import LLMConfigurationError

    # Production + placeholder key + real OpenAI target -> loud failure.
    _set(
        monkeypatch,
        LLM_PROVIDER="openai",
        LLM_BASE_URL=None,
        ENVIRONMENT="production",
        OPENAI_API_KEY=config_module.INSECURE_OPENAI_KEY,
        LLM_API_KEY=None,
    )
    with pytest.raises(LLMConfigurationError):
        get_llm_provider()

    # Same config in development is tolerated (calls are mocked / local).
    _set(monkeypatch, ENVIRONMENT="development")
    assert isinstance(get_llm_provider(), OpenAICompatLLMProvider)

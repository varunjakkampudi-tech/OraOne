"""AI provider resilience — provider outages must surface, not fabricate data."""
from __future__ import annotations

import pytest

from app.providers.base import AIProviderError, ChatMessage


class _AlwaysFailsProvider:
    """Simulates a fully-down AI provider (e.g. network outage, revoked key)."""

    async def chat(self, messages, *, model, temperature=0.7, max_tokens=1024):
        raise AIProviderError("simulated provider outage", code="network")


@pytest.mark.asyncio
async def test_generate_reply_surfaces_provider_error_when_chain_exhausted(monkeypatch):
    from app.services import agent_runtime as runtime_module

    runtime = object.__new__(runtime_module.AgentRuntime)
    runtime.provider = _AlwaysFailsProvider()
    runtime.session = None
    runtime.ctx = None

    def _fake_model_params(agent):
        return "openai/gpt-5.5", 0.7, 100

    async def _fake_route_chain(model):
        return [model]  # single-model chain, all of which fail

    monkeypatch.setattr(runtime, "_model_params", _fake_model_params)
    monkeypatch.setattr(runtime, "_route_chain", _fake_route_chain)

    with pytest.raises(AIProviderError, match="simulated provider outage"):
        await runtime.generate_reply(agent=None, messages=[ChatMessage(role="user", content="hi")])


def test_mock_provider_is_forbidden_in_production(monkeypatch):
    from app.providers import get_provider

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AI_ALLOW_MOCK", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_provider.cache_clear()

    with pytest.raises(RuntimeError, match="forbidden in production-like"):
        get_provider()

    get_provider.cache_clear()


def test_mock_provider_remains_available_for_local_tests(monkeypatch):
    from app.providers import get_provider

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("AI_ALLOW_MOCK", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_provider.cache_clear()

    provider = get_provider()
    assert provider.name == "mock"
    get_provider.cache_clear()

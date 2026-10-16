"""AI provider behaviour: outages surface to the caller and configuration is enforced."""

from __future__ import annotations

import pytest

from app.providers.base import AIProviderError, ChatMessage


class _AlwaysFailsProvider:
    """A fully unavailable provider, for example after a network outage or a revoked key."""

    async def chat(self, messages, *, model, temperature=0.7, max_tokens=1024):
        raise AIProviderError("simulated provider outage", code="network")


@pytest.mark.asyncio
async def test_generate_reply_surfaces_provider_error_when_chain_exhausted(monkeypatch):
    """A failing model chain must raise, never return fabricated text."""
    from app.services import agent_runtime as runtime_module

    runtime = object.__new__(runtime_module.AgentRuntime)
    runtime.provider = _AlwaysFailsProvider()
    runtime.session = None
    runtime.ctx = None

    def _fake_model_params(agent):
        return "google/gemini-2.5-flash", 0.7, 100

    async def _fake_route_chain(model):
        return [model]  # single-model chain, which fails

    monkeypatch.setattr(runtime, "_model_params", _fake_model_params)
    monkeypatch.setattr(runtime, "_route_chain", _fake_route_chain)

    with pytest.raises(AIProviderError, match="simulated provider outage"):
        await runtime.generate_reply(
            agent=None, messages=[ChatMessage(role="user", content="hi")]
        )


def test_provider_requires_openrouter_key(monkeypatch):
    """Without OPENROUTER_API_KEY the app refuses to start inference."""
    from app.providers import get_provider

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    get_provider.cache_clear()

    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY is required"):
        get_provider()

    get_provider.cache_clear()


def test_provider_is_openrouter_when_key_is_set(monkeypatch):
    """With a key the factory returns the OpenRouter provider."""
    from app.providers import get_provider

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key")
    get_provider.cache_clear()

    provider = get_provider()
    assert provider.name == "openrouter"
    get_provider.cache_clear()

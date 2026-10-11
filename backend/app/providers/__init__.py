"""AI provider package (Phase 8).

Exposes the provider contract plus a tiny factory that selects the right
backend from environment configuration. Importing this package is cheap
and side-effect free.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

from app.providers.base import (
    AIProvider,
    AIProviderError,
    AIResponse,
    ChatMessage,
    TokenUsage,
    estimate_tokens,
)

log = logging.getLogger("app.providers")

#: Default model. Overridable via ``OPENAI_MODEL``.
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "openai/gpt-5.5")


@lru_cache(maxsize=1)
def get_provider() -> AIProvider:
    """Return the active AI provider.

    Selection rules:
      * ``OPENAI_API_KEY`` present  → :class:`OpenAIProvider`
      * otherwise                   → fail closed unless explicit mock mode is enabled

    The result is cached for the process; tests can clear it via
    ``get_provider.cache_clear()``.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    environment = os.environ.get("ENVIRONMENT", "development").strip().lower()
    if environment in {"production", "prod", "staging"} and os.environ.get(
        "AI_ALLOW_MOCK", "false"
    ).strip().lower() == "true":
        raise RuntimeError("AI_ALLOW_MOCK is forbidden in production-like environments.")
    if api_key:
        try:
            from app.providers.openai_provider import OpenAIProvider

            base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
            log.info(
                "AI provider: openai (model=%s, base_url=%s)",
                DEFAULT_MODEL,
                base_url or "default",
            )
            return OpenAIProvider(api_key, base_url=base_url)
        except Exception as e:  # pragma: no cover - defensive
            raise RuntimeError("OpenRouter provider initialization failed") from e
    if os.environ.get("AI_ALLOW_MOCK", "false").strip().lower() == "true":
        from app.providers.mock_provider import MockProvider
        log.warning("AI provider: explicit mock mode enabled")
        return MockProvider()
    raise RuntimeError(
        "OPENAI_API_KEY is required for AI inference. "
        "Set AI_ALLOW_MOCK=true only in isolated development/test environments."
    )


__all__ = [
    "AIProvider",
    "AIProviderError",
    "AIResponse",
    "ChatMessage",
    "TokenUsage",
    "DEFAULT_MODEL",
    "get_provider",
    "estimate_tokens",
]

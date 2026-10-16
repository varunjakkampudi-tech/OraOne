"""AI provider package.

OraOne uses OpenRouter for every model call. This package exposes the provider
contract and a factory that builds the OpenRouter client from configuration.
Importing the package is cheap and has no side effects.
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

#: Default model id, overridable with ``OPENROUTER_MODEL``.
DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-5.5")


@lru_cache(maxsize=1)
def get_provider() -> AIProvider:
    """Return the OpenRouter provider, or fail if no API key is configured.

    The result is cached for the process. Tests can clear it with
    ``get_provider.cache_clear()``.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is required for AI inference. "
            "Create a key at https://openrouter.ai and set it in backend/.env."
        )
    from app.providers.openrouter_provider import OpenRouterProvider

    base_url = os.environ.get("OPENROUTER_BASE_URL", "").strip() or None
    log.info("AI provider: openrouter (model=%s)", DEFAULT_MODEL)
    return OpenRouterProvider(api_key, base_url=base_url)


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

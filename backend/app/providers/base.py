"""AI provider abstraction (Phase 8).

The agent runtime never talks to a vendor SDK directly — it talks to an
:class:`AIProvider`. This keeps OpenAI (and future Claude / Gemini /
Bedrock) behind one small, swappable seam so the rest of the app is
model-agnostic.

Concrete providers live alongside this module:

* :class:`~app.providers.openai_provider.OpenAIProvider`
* :class:`~app.providers.mock_provider.MockProvider`  (offline / no-key dev)
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional


@dataclass
class ChatMessage:
    """A single turn in the model-facing conversation."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str

    def as_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class TokenUsage:
    """Token accounting for one completion. Drives future billing."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class AIResponse:
    """A finished (non-streamed) completion."""

    content: str
    model: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    finish_reason: str = "stop"


class AIProviderError(Exception):
    """Normalised provider failure.

    ``code`` is a stable, vendor-agnostic string the API layer can map to
    an HTTP status / user-facing message without leaking SDK internals:

    ``timeout`` | ``rate_limit`` | ``auth`` | ``context_overflow`` |
    ``network`` | ``provider`` | ``unknown``
    """

    def __init__(self, message: str, *, code: str = "unknown", retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class AIProvider(abc.ABC):
    """Vendor-neutral chat-completion interface."""

    #: Human-readable provider id used in logs / metadata.
    name: str = "base"

    @abc.abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AIResponse:
        """Return a single completion for ``messages``."""

    @abc.abstractmethod
    def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """Yield completion text deltas as they arrive.

        Implementations are async generators. The final accumulated text
        equals what :meth:`chat` would have returned.
        """
        raise NotImplementedError


def estimate_tokens(text: str) -> int:
    """Cheap, dependency-free token estimate (~4 chars/token).

    Good enough for the mock provider and as a fallback when a real
    provider doesn't report usage. Never returns 0 for non-empty text.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)

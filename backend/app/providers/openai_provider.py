"""OpenAI AI provider (Phase 8).

Wraps the official ``openai`` Async SDK behind the vendor-neutral
:class:`AIProvider` contract. The SDK is imported lazily so the rest of
the app (and the mock provider) work even when ``openai`` isn't
installed.

Model is configurable via ``OPENAI_MODEL`` (default ``openai/gpt-5.5``).
"""
from __future__ import annotations

import logging
import os
import re
from typing import AsyncIterator

from app.providers.base import (
    AIProvider,
    AIProviderError,
    AIResponse,
    ChatMessage,
    TokenUsage,
    estimate_tokens,
)

log = logging.getLogger("app.providers.openai")

_DEFAULT_TIMEOUT = float(os.environ.get("OPENAI_TIMEOUT", "60"))

# Bedrock-hosted OpenAI gpt-oss models inline chain-of-thought inside
# <reasoning>...</reasoning> before the final answer. Strip it so the
# reasoning never leaks into user-facing responses. Harmless for models
# that don't emit these tags.
_REASONING_RE = re.compile(r"<reasoning>.*?</reasoning>", re.DOTALL)
_REASONING_OPEN = "<reasoning>"
_REASONING_CLOSE = "</reasoning>"


def _strip_reasoning(text: str) -> str:
    if _REASONING_OPEN not in text:
        return text
    return _REASONING_RE.sub("", text).lstrip()


class _ReasoningStreamFilter:
    """Incrementally strips ``<reasoning>...</reasoning>`` blocks from a token
    stream. Handles *multiple* reasoning blocks and tags split across chunks.
    """

    def __init__(self) -> None:
        self._buf = ""
        self._in_reasoning = False
        self._emitted = False

    def feed(self, piece: str) -> str:
        self._buf += piece
        out = ""
        while True:
            if self._in_reasoning:
                ci = self._buf.find(_REASONING_CLOSE)
                if ci == -1:
                    # Drop reasoning content; keep a small tail in case the
                    # closing tag is split across the next chunk.
                    tail = len(_REASONING_CLOSE) - 1
                    if len(self._buf) > tail:
                        self._buf = self._buf[-tail:]
                    break
                self._buf = self._buf[ci + len(_REASONING_CLOSE):]
                self._in_reasoning = False
                continue
            oi = self._buf.find(_REASONING_OPEN)
            if oi == -1:
                # Emit all but a possible partial opening tag at the tail.
                keep = 0
                for k in range(min(len(_REASONING_OPEN) - 1, len(self._buf)), 0, -1):
                    if self._buf[-k:] == _REASONING_OPEN[:k]:
                        keep = k
                        break
                emit = self._buf[: len(self._buf) - keep] if keep else self._buf
                self._buf = self._buf[len(self._buf) - keep:] if keep else ""
                out += emit
                break
            out += self._buf[:oi]
            self._buf = self._buf[oi + len(_REASONING_OPEN):]
            self._in_reasoning = True
        if out and not self._emitted:
            out = out.lstrip()
            if out:
                self._emitted = True
        return out

    def flush(self) -> str:
        if self._in_reasoning:
            return ""
        leftover, self._buf = self._buf, ""
        return leftover


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        base_url: str | None = None,
    ):
        self._api_key = api_key
        self._timeout = timeout
        self._base_url = (base_url or "").strip() or None
        self._client = None  # lazily constructed

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import AsyncOpenAI  # type: ignore
        except ImportError as e:  # pragma: no cover - env dependent
            raise AIProviderError(
                "The 'openai' package is not installed.",
                code="provider",
            ) from e
        kwargs = {"api_key": self._api_key, "timeout": self._timeout}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        # OpenRouter uses HTTP-Referer / X-Title for app attribution and
        # leaderboard ranking. Send them automatically when pointed at it.
        if self._base_url and "openrouter.ai" in self._base_url:
            site = os.environ.get("OPENROUTER_SITE_URL", "https://oraone.in").strip()
            title = os.environ.get("OPENROUTER_APP_NAME", "OraOne").strip()
            kwargs["default_headers"] = {"HTTP-Referer": site, "X-Title": title}
        self._client = AsyncOpenAI(**kwargs)
        return self._client

    def _translate_error(self, exc: Exception) -> AIProviderError:
        """Map vendor exceptions onto stable, user-safe error codes."""
        name = type(exc).__name__
        msg = str(exc)
        if name in ("APITimeoutError", "Timeout", "TimeoutError"):
            return AIProviderError("The AI provider timed out.", code="timeout", retryable=True)
        if name in ("RateLimitError",):
            return AIProviderError("The AI provider is rate limited.", code="rate_limit", retryable=True)
        if name in ("AuthenticationError", "PermissionDeniedError"):
            return AIProviderError("Invalid AI provider credentials.", code="auth")
        if name in ("APIConnectionError", "APIConnectionTimeoutError"):
            return AIProviderError("Could not reach the AI provider.", code="network", retryable=True)
        if "context length" in msg.lower() or "maximum context" in msg.lower():
            return AIProviderError("The conversation exceeded the model context window.", code="context_overflow")
        return AIProviderError(f"AI provider error: {msg}", code="provider")

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AIResponse:
        client = self._get_client()
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[m.as_dict() for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
        except Exception as exc:  # noqa: BLE001 — normalised below
            raise self._translate_error(exc) from exc

        choice = resp.choices[0]
        content = _strip_reasoning(choice.message.content or "")
        usage = getattr(resp, "usage", None)
        if usage is not None:
            token_usage = TokenUsage(
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                total_tokens=getattr(usage, "total_tokens", 0) or 0,
            )
        else:  # pragma: no cover - usage almost always present
            pt = sum(estimate_tokens(m.content) for m in messages)
            ct = estimate_tokens(content)
            token_usage = TokenUsage(pt, ct, pt + ct)

        return AIResponse(
            content=content,
            model=getattr(resp, "model", model),
            usage=token_usage,
            finish_reason=getattr(choice, "finish_reason", "stop") or "stop",
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        client = self._get_client()
        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=[m.as_dict() for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            buffer = ""
            reasoning_resolved = False
            rfilter = _ReasoningStreamFilter()
            async for event in stream:
                if not event.choices:
                    continue
                delta = event.choices[0].delta
                piece = getattr(delta, "content", None)
                if not piece:
                    continue
                out = rfilter.feed(piece)
                if out:
                    yield out
            leftover = rfilter.flush()
            if leftover:
                yield leftover
        except Exception as exc:  # noqa: BLE001 — normalised below
            raise self._translate_error(exc) from exc

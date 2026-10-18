"""The signed-in chat runtime applies the same grounding rule as the public widget.

No network and no real model: the provider is a canned fake, and the model
chain is pinned to one model.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.providers.base import AIResponse
from app.services import agent_runtime, grounding
from app.services.agent_runtime import AgentRuntime

PASSAGE = "The Starter plan costs 499 rupees a month."


class _FakeProvider:
    def __init__(self, content: str) -> None:
        self.content = content

    async def chat(self, messages, **kwargs):
        return AIResponse(content=self.content, model="fake/model")


def _runtime(monkeypatch, content: str) -> AgentRuntime:
    monkeypatch.setattr(agent_runtime, "get_provider", lambda: _FakeProvider(content))
    runtime = AgentRuntime(
        session=None, ctx=SimpleNamespace(organization_id=uuid.uuid4())
    )
    monkeypatch.setattr(
        runtime, "_model_params", lambda agent: ("fake/model", 0.2, 100)
    )

    async def _chain(model):
        return [model]

    monkeypatch.setattr(runtime, "_route_chain", _chain)
    return runtime


def test_enforce_keeps_a_supported_reply():
    answer, changed = grounding.enforce_grounded(
        "The Starter plan costs 499 rupees a month.", [PASSAGE]
    )
    assert changed is False
    assert answer == "The Starter plan costs 499 rupees a month."


def test_enforce_replaces_an_invented_reply_with_passage_text():
    answer, changed = grounding.enforce_grounded(
        "The Starter plan costs 599 rupees and includes a free domain.", [PASSAGE]
    )
    assert changed is True
    assert grounding.FALLBACK_PREFIX in answer
    assert PASSAGE in answer


def test_enforce_without_passages_leaves_the_reply_alone():
    answer, changed = grounding.enforce_grounded("Anything at all.", [])
    assert (answer, changed) == ("Anything at all.", False)


@pytest.mark.asyncio
async def test_runtime_reply_is_grounded_when_passages_are_given(monkeypatch):
    runtime = _runtime(monkeypatch, "The Starter plan costs 599 rupees.")
    resp = await runtime.generate_reply(SimpleNamespace(), [], passages=[PASSAGE])
    assert "599" not in resp.content
    assert PASSAGE in resp.content


@pytest.mark.asyncio
async def test_runtime_reply_is_untouched_without_passages(monkeypatch):
    runtime = _runtime(monkeypatch, "The Starter plan costs 599 rupees.")
    resp = await runtime.generate_reply(SimpleNamespace(), [])
    assert resp.content == "The Starter plan costs 599 rupees."


def test_stream_chunks_rebuild_the_exact_text():
    from app.api.chat.routes import _text_chunks

    text = "Refunds take five business days and go to the original payment method."
    pieces = _text_chunks(text, 20)
    assert len(pieces) > 1
    assert "".join(pieces) == text
    assert all(len(p) <= 21 for p in pieces)


def test_streamed_invented_reply_is_replaced_before_chunking():
    from app.api.chat.routes import _text_chunks

    invented = "The Starter plan costs 599 rupees and includes a free domain."
    final, changed = grounding.enforce_grounded(invented, [PASSAGE])
    assert changed is True
    assert "599" not in "".join(_text_chunks(final, 60))

"""Fallback replies must say they are fallbacks (``generated`` is false).

No test contacts a real model: the provider is replaced with a fake that either
returns JSON or raises, so the API contract is exercised end to end.
"""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.middleware.org_context import OrgContext, get_current_organization
from app.services import assistants, rag_answer, rag_service


def _ctx() -> OrgContext:
    return OrgContext(
        user_id=uuid.uuid4(),
        auth_subject="sub-assistant",
        organization_id=uuid.uuid4(),
        membership_role="owner",
    )


class _FailingProvider:
    async def chat(self, messages, **kwargs):
        raise RuntimeError("model offline")


class _JsonProvider:
    def __init__(self, payload: dict):
        self._payload = payload

    async def chat(self, messages, **kwargs):
        return SimpleNamespace(content=json.dumps(self._payload))


@pytest.fixture
def api_client():
    from server import app

    async def _override() -> OrgContext:
        return _ctx()

    app.dependency_overrides[get_current_organization] = _override
    try:
        yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    finally:
        app.dependency_overrides.pop(get_current_organization, None)


@pytest.mark.asyncio
async def test_assistant_fallback_reply_carries_generated_false(
    api_client, monkeypatch
):
    monkeypatch.setattr(assistants, "get_provider", lambda: _FailingProvider())
    async with api_client as client:
        r = await client.post(
            "/api/assistants/meeting/run",
            json={"input": {"transcript": "We agreed to ship on Friday."}},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["generated"] is False
    assert body["result"]["summary"].startswith("AI summary unavailable")


@pytest.mark.asyncio
async def test_assistant_model_reply_carries_generated_true(api_client, monkeypatch):
    payload = {
        "summary": "Ship on Friday.",
        "action_items": [],
        "decisions": ["Ship on Friday"],
        "follow_ups": [],
        "sentiment": "positive",
    }
    monkeypatch.setattr(assistants, "get_provider", lambda: _JsonProvider(payload))
    async with api_client as client:
        r = await client.post(
            "/api/assistants/meeting/run",
            json={"input": {"transcript": "We agreed to ship on Friday."}},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["generated"] is True
    assert body["result"]["summary"] == "Ship on Friday."


@pytest.mark.asyncio
async def test_experiment_fallback_does_not_recommend_a_fixed_variant(
    api_client, monkeypatch
):
    monkeypatch.setattr(assistants, "get_provider", lambda: _FailingProvider())
    async with api_client as client:
        r = await client.post(
            "/api/assistants/experiment/run",
            json={"input": {"variant_a": "Buy now", "variant_b": "Try free"}},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["generated"] is False
    assert body["result"]["recommended_variant"] is None
    assert body["result"]["confidence"] == "none"
    assert "No comparison was produced" in body["result"]["rationale"]


def test_experiment_fallback_helper_has_no_fixed_winner():
    out = assistants.ASSISTANTS["experiment"].fallback({})
    assert out["recommended_variant"] not in ("A", "B")


@pytest.mark.asyncio
async def test_rag_answer_fallback_is_flagged_not_generated(monkeypatch):
    chunk = rag_service.RetrievedChunk(
        content="Refunds are processed within five business days.",
        chunk_index=0,
        document_name="Refund policy",
        score=0.9,
    )

    async def _one_chunk(*_args, **_kwargs):
        return [chunk]

    monkeypatch.setattr(rag_answer.rag_service, "hybrid_search", _one_chunk)
    monkeypatch.setattr(rag_answer, "get_provider", lambda: _FailingProvider())

    result = await rag_answer.answer_query(
        object(), "How long do refunds take?", uuid.uuid4(), persona=None
    )
    assert result["generated"] is False
    assert "Refunds are processed" in result["answer"]


@pytest.mark.asyncio
async def test_rag_answer_model_reply_is_flagged_generated(monkeypatch):
    chunk = rag_service.RetrievedChunk(
        content="Refunds are processed within five business days.",
        chunk_index=0,
        document_name="Refund policy",
        score=0.9,
    )

    async def _one_chunk(*_args, **_kwargs):
        return [chunk]

    class _Provider:
        async def chat(self, messages, **kwargs):
            return SimpleNamespace(
                content="Refunds take five business days [1].",
                model="test/model",
                usage=None,
            )

    monkeypatch.setattr(rag_answer.rag_service, "hybrid_search", _one_chunk)
    monkeypatch.setattr(rag_answer, "get_provider", lambda: _Provider())

    result = await rag_answer.answer_query(
        object(), "How long do refunds take?", uuid.uuid4(), persona=None
    )
    assert result["generated"] is True
    assert result["answer"] == "Refunds take five business days [1]."

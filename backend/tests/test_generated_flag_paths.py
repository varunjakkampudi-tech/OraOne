"""Fallback replies say they are fallbacks on every reply path that calls ``answer_query``.

The public widget chat returns ``generated`` on the response and stores it on the agent
message metadata. The omnichannel path records it on the message metadata only: the reply
text sent to the customer is unchanged.

No database, no network, no real model. ``answer_query`` is replaced with a canned result.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.widgets import public
from app.database.models.agent import AgentStatus
from app.database.models.message import MessageSender
from app.database.session import get_db
from app.services import lead_service, omnichannel_service
from app.services import visitor_service, widget_service, workflow_triggers

TEST_PROJECT_ID = uuid.uuid4()

FALLBACK_TEXT = (
    "I couldn't find anything relevant in your knowledge base for that question. "
    "Try rephrasing, or add documents / websites that cover this topic."
)


def _rag_result(*, answer: str, generated: bool) -> dict[str, Any]:
    return {
        "answer": answer,
        "sources": [],
        "confidence": 0.0,
        "related_questions": [],
        "context_chunks": 0,
        "grounded": False,
        "generated": generated,
        "model": None,
    }


class _Session:
    """Records adds and answers the one agent lookup. Nothing is written."""

    def __init__(self, agent_row: Optional[SimpleNamespace] = None) -> None:
        self._agent_row = agent_row
        self.added: list[Any] = []
        self.commits = 0

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def scalar(self, _stmt: Any) -> Any:
        return self._agent_row

    def agent_messages(self) -> list[Any]:
        return [
            m for m in self.added if getattr(m, "sender", None) == MessageSender.agent
        ]


# ───────────────────────── omnichannel ─────────────────────────


def _inbound() -> omnichannel_service.InboundMessage:
    return omnichannel_service.InboundMessage(
        channel="whatsapp",
        organization_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        project_id=None,
        text="When do you open?",
        phone="+14155550123",
        provider_message_id="whatsapp:wamid.1",
    )


def _patch_omnichannel(monkeypatch: pytest.MonkeyPatch, *, rag: dict[str, Any]) -> None:
    async def _claim(_session, _msg):
        return True

    async def _thread(_session, _msg, _profile, _channel):
        return SimpleNamespace(id=uuid.uuid4())

    async def _upsert(*_args, **_kwargs):
        return SimpleNamespace()

    async def _answer(*_args, **_kwargs):
        return rag

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(omnichannel_service, "_claim_provider_message", _claim)
    monkeypatch.setattr(omnichannel_service, "_find_or_create_thread", _thread)
    monkeypatch.setattr(omnichannel_service, "answer_query", _answer)
    monkeypatch.setattr(visitor_service, "upsert_profile", _upsert)
    monkeypatch.setattr(visitor_service, "link_conversation", lambda *a, **k: None)
    monkeypatch.setattr(visitor_service, "build_memory_digest", lambda *a, **k: "")
    monkeypatch.setattr(visitor_service, "append_memory", lambda *a, **k: None)
    monkeypatch.setattr(workflow_triggers, "fire_message_received", _noop)


@pytest.mark.asyncio
async def test_omnichannel_fallback_is_recorded_as_not_generated(monkeypatch):
    _patch_omnichannel(
        monkeypatch, rag=_rag_result(answer=FALLBACK_TEXT, generated=False)
    )
    session = _Session()

    reply = await omnichannel_service.handle_inbound(session, _inbound())

    assert reply.generated is False
    assert reply.handled is True
    # The text sent to the customer is exactly what answer_query returned.
    assert reply.text == FALLBACK_TEXT
    [agent_msg] = session.agent_messages()
    assert agent_msg.message == FALLBACK_TEXT
    assert agent_msg.metadata_["generated"] is False
    assert agent_msg.metadata_["channel"] == "whatsapp"


@pytest.mark.asyncio
async def test_omnichannel_model_reply_is_recorded_as_generated(monkeypatch):
    answer = "We open at 9am on weekdays."
    _patch_omnichannel(monkeypatch, rag=_rag_result(answer=answer, generated=True))
    session = _Session()

    reply = await omnichannel_service.handle_inbound(session, _inbound())

    assert reply.generated is True
    assert reply.text == answer
    [agent_msg] = session.agent_messages()
    assert agent_msg.metadata_["generated"] is True


# ───────────────────────── public widget chat ─────────────────────────


def _widget_client(
    monkeypatch: pytest.MonkeyPatch, *, rag: dict[str, Any]
) -> tuple[TestClient, _Session]:
    widget = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        project_id=None,
        public_key="pk_live_generated_flag",
        agent_id=uuid.uuid4(),
        knowledge_base_id=None,
    )
    ws = SimpleNamespace(
        id=uuid.uuid4(),
        visitor_id="visitor-1",
        conversation_id=None,
        user_context={},
        message_count=0,
        last_active_at=None,
    )
    # An active agent with no config: the widget's own knowledge-base scope applies.
    session = _Session(
        agent_row=SimpleNamespace(status=AgentStatus.active, config=None, model=None)
    )

    async def _load(_session, _key, *, origin, referer, require_published=True):
        return widget

    async def _chat_session(_session, _widget, **_kwargs):
        return ws, "session-token"

    async def _resolve(_session, _widget):
        return widget.agent_id

    async def _answer(*_args, **_kwargs):
        return rag

    async def _noop(*_args, **_kwargs):
        return None

    async def _upsert(*_args, **_kwargs):
        return SimpleNamespace()

    monkeypatch.setattr(public, "_load_live_widget", _load)
    monkeypatch.setattr(public, "_chat_visitor_session", _chat_session)
    monkeypatch.setattr(public, "_check_ip_rate", lambda *a, **k: None)
    monkeypatch.setattr(public, "_check_rate", lambda *a, **k: None)
    monkeypatch.setattr(public, "answer_query", _answer)
    monkeypatch.setattr(widget_service, "resolve_agent_id", _resolve)
    monkeypatch.setattr(widget_service, "log_event", _noop)
    monkeypatch.setattr(lead_service, "upsert_conversation_lead", _noop)
    monkeypatch.setattr(visitor_service, "upsert_profile", _upsert)
    monkeypatch.setattr(visitor_service, "link_conversation", lambda *a, **k: None)
    monkeypatch.setattr(visitor_service, "build_memory_digest", lambda *a, **k: "")
    monkeypatch.setattr(visitor_service, "append_memory", lambda *a, **k: None)

    app = FastAPI()
    app.include_router(public.public_router)
    app.dependency_overrides[get_db] = lambda: session
    return TestClient(app), session


def _chat(client: TestClient):
    return client.post(
        "/api/widget/chat",
        json={
            "public_key": "pk_live_generated_flag",
            "visitor_id": "visitor-1",
            "message": "When do you open?",
        },
        headers={"origin": "https://shop.example.com"},
    )


def test_widget_fallback_reply_carries_generated_false(monkeypatch):
    client, session = _widget_client(
        monkeypatch, rag=_rag_result(answer=FALLBACK_TEXT, generated=False)
    )

    response = _chat(client)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["generated"] is False
    assert body["answer"] == FALLBACK_TEXT
    [agent_msg] = session.agent_messages()
    assert agent_msg.metadata_["generated"] is False


def test_widget_model_reply_carries_generated_true(monkeypatch):
    answer = "We open at 9am on weekdays."
    client, session = _widget_client(
        monkeypatch, rag=_rag_result(answer=answer, generated=True)
    )

    response = _chat(client)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["generated"] is True
    assert body["answer"] == answer
    [agent_msg] = session.agent_messages()
    assert agent_msg.metadata_["generated"] is True


@pytest.fixture(autouse=True)
def _default_project_for_tests(monkeypatch):
    """Customer paths resolve a project. These tests have no project rows, so
    the organization default is pinned to one fixed project."""
    from app.services import project_scope

    project = uuid.uuid4()

    async def _default(_session, _organization_id):
        return project

    monkeypatch.setattr(project_scope, "default_project_id", _default)

"""Public widget visitor security: session tokens, IP rate limits, no-lead on reject.

No database and no network. Widget and visitor rows are in-memory model
instances, the shared rate-limit cache is replaced by a counter, and the
public router is mounted on a small FastAPI app.
"""

from __future__ import annotations

import base64
import hashlib
import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.widgets import public
from app.database.models.message import MessageSender
from app.database.models.widget import WidgetStatus
from app.database.models.widget_session import WidgetSession
from app.database.session import get_db
from app.services import lead_service, widget_service

ORG = uuid.uuid4()
KEY = "pk_live_security_widget"


class _Rows:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)


class FakeSession:
    """Just enough of AsyncSession for the public endpoints under test."""

    def __init__(self):
        self.added: list = []
        self.messages: list = []
        self.scalar_value = None
        self.commits = 0

    def add(self, obj):
        # The database assigns primary keys on flush; mirror that here.
        if isinstance(obj, WidgetSession) and obj.id is None:
            obj.id = uuid.uuid4()
        self.added.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        self.commits += 1

    async def scalar(self, *args, **kwargs):
        return self.scalar_value

    async def scalars(self, *args, **kwargs):
        return _Rows(self.messages)


def _sha(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    # The fake environment has no project rows. Pin the organization default so
    # the escalation path resolves a project, as it does in production.
    from app.services import project_scope

    default_project = uuid.uuid4()

    async def _default(_session, _organization_id):
        return default_project

    monkeypatch.setattr(project_scope, "default_project_id", _default)
    monkeypatch.setenv("WIDGET_IP_RATE_LIMIT_PER_MIN", "1000")
    for name in (
        "WIDGET_CDN_BASE",
        "WIDGET_API_BASE",
        "BACKEND_PUBLIC_URL",
        "PUBLIC_BACKEND_URL",
        "BACKEND_URL",
    ):
        monkeypatch.delenv(name, raising=False)

    widget = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=ORG,
        project_id=None,
        public_key=KEY,
        status=WidgetStatus.published,
        settings={},
        deleted_at=None,
        agent_id=None,
        knowledge_base_id=None,
    )
    counters: dict[str, int] = {}

    def limiter(key, *, limit, window_seconds=60):
        counters[key] = counters.get(key, 0) + 1
        return counters[key] > max(1, limit)

    async def by_key(session, key):
        return widget if key == KEY else None

    async def domains(session, widget_id):
        return []

    logged: list = []

    async def log_event(session, *, widget, event, session_id=None, metadata=None):
        logged.append(SimpleNamespace(event=event, session_id=session_id))

    leads: list = []

    async def upsert_lead(session, **kwargs):
        leads.append(kwargs)

    answered: list = []

    async def persist(session, widget, ws, text):
        answered.append(text)
        return {
            "answer": "ok",
            "sources": [],
            "confidence": 0.9,
            "related_questions": [],
            "grounded": True,
            "conversation_id": None,
            "message_id": None,
        }

    async def find_visitor(session, w, visitor_id):
        rows = [
            o
            for o in session.added
            if isinstance(o, WidgetSession)
            and o.widget_id == w.id
            and o.visitor_id == visitor_id
        ]
        return rows[-1] if rows else None

    monkeypatch.setattr(widget_service, "rate_limited", limiter)
    monkeypatch.setattr(widget_service, "get_widget_by_key", by_key)
    monkeypatch.setattr(widget_service, "widget_domains", domains)
    monkeypatch.setattr(widget_service, "log_event", log_event)
    monkeypatch.setattr(lead_service, "upsert_conversation_lead", upsert_lead)
    monkeypatch.setattr(public, "_persist_and_answer", persist)
    monkeypatch.setattr(public, "_find_visitor_session", find_visitor)

    fake = FakeSession()
    app = FastAPI()
    app.include_router(public.public_router)
    app.dependency_overrides[get_db] = lambda: fake
    return SimpleNamespace(
        client=TestClient(app),
        session=fake,
        widget=widget,
        counters=counters,
        logged=logged,
        leads=leads,
        answered=answered,
        monkeypatch=monkeypatch,
    )


def _seed(env, *, visitor_id, token=None, conversation_id=None, legacy=False):
    """Add a visitor session row. Only the digest is stored, as in production."""
    digest = None if (legacy or token is None) else _sha(token)
    ws = WidgetSession(
        id=uuid.uuid4(),
        widget_id=env.widget.id,
        organization_id=ORG,
        visitor_id=visitor_id,
        user_context={},
        session_token_hash=digest,
    )
    ws.conversation_id = conversation_id
    env.session.added.append(ws)
    return ws


def _start(env, visitor_id=None, token=None, extra_headers=None):
    headers = dict(extra_headers or {})
    if token is not None:
        headers["X-Widget-Session"] = token
    body = {"public_key": KEY}
    if visitor_id is not None:
        body["visitor_id"] = visitor_id
    return env.client.post("/api/widget/session", json=body, headers=headers)


def _lead(env, visitor_id, token=None, **extra):
    headers = {"X-Widget-Session": token} if token is not None else {}
    body = {
        "public_key": KEY,
        "visitor_id": visitor_id,
        "email": "a@example.com",
        **extra,
    }
    return env.client.post("/api/widget/lead", json=body, headers=headers)


def _chat(env, visitor_id, token=None, message="hello", headers=None):
    all_headers = dict(headers or {})
    if token is not None:
        all_headers["X-Widget-Session"] = token
    return env.client.post(
        "/api/widget/chat",
        json={"public_key": KEY, "visitor_id": visitor_id, "message": message},
        headers=all_headers,
    )


# ── transcript access ────────────────────────────────────────────────────────


def test_session_restore_without_token_returns_no_transcript(env):
    token = "A" * 43
    conv = uuid.uuid4()
    _seed(env, visitor_id="visitor-a", token=token, conversation_id=conv)
    env.session.messages = [
        SimpleNamespace(
            sender=MessageSender.customer,
            message="my secret order number",
            created_at=None,
        )
    ]

    response = _start(env, visitor_id="visitor-a")

    assert response.status_code == 200
    body = response.json()
    assert body["messages"] == []
    assert body["conversation_id"] is None
    assert body["visitor_id"] != "visitor-a"
    assert body["session_token"]
    assert "secret order number" not in response.text


def test_session_restore_with_the_visitors_own_token_returns_transcript(env):
    token = "B" * 43
    conv = uuid.uuid4()
    _seed(env, visitor_id="visitor-a", token=token, conversation_id=conv)
    env.session.messages = [
        SimpleNamespace(
            sender=MessageSender.customer, message="hi there", created_at=None
        )
    ]

    response = _start(env, visitor_id="visitor-a", token=token)

    body = response.json()
    assert body["visitor_id"] == "visitor-a"
    assert body["conversation_id"] == str(conv)
    assert [m["content"] for m in body["messages"]] == ["hi there"]
    assert body["session_token"] is None


def test_token_for_visitor_a_cannot_read_visitor_b(env):
    token_a = "C" * 43
    token_b = "D" * 43
    _seed(env, visitor_id="visitor-a", token=token_a, conversation_id=uuid.uuid4())
    _seed(env, visitor_id="visitor-b", token=token_b, conversation_id=uuid.uuid4())
    env.session.messages = [
        SimpleNamespace(
            sender=MessageSender.customer,
            message="B's private transcript",
            created_at=None,
        )
    ]

    response = _start(env, visitor_id="visitor-b", token=token_a)

    assert response.json()["messages"] == []
    assert "private transcript" not in response.text


def test_legacy_visitor_without_a_digest_fails_closed(env):
    _seed(env, visitor_id="legacy-visitor", legacy=True, conversation_id=uuid.uuid4())
    env.session.messages = [
        SimpleNamespace(
            sender=MessageSender.customer, message="legacy transcript", created_at=None
        )
    ]

    # Any token, including an empty-looking one, must not match a row with no digest.
    response = _start(env, visitor_id="legacy-visitor", token="anything")
    assert response.json()["messages"] == []
    assert "legacy transcript" not in response.text

    lead = _lead(env, "legacy-visitor", token="anything")
    assert lead.status_code == 403
    assert env.leads == []


def test_chat_issues_a_token_once_and_stores_only_its_digest(env):
    response = _chat(env, "new-visitor")

    assert response.status_code == 200
    token = response.json()["session_token"]
    assert token
    decoded = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    assert len(decoded) == 32

    stored = [o for o in env.session.added if isinstance(o, WidgetSession)]
    assert len(stored) == 1
    assert stored[0].session_token_hash == _sha(token)
    assert token not in stored[0].session_token_hash

    # A later message without the token is refused; with it, the chat proceeds.
    assert _chat(env, "new-visitor").status_code == 403
    second = _chat(env, "new-visitor", token=token)
    assert second.status_code == 200
    assert second.json()["session_token"] is None


def test_chat_for_an_existing_visitor_requires_its_token(env):
    token = "E" * 43
    _seed(env, visitor_id="visitor-a", token=token)

    assert _chat(env, "visitor-a", token="F" * 43).status_code == 403
    assert _chat(env, "visitor-a").status_code == 403
    assert env.answered == []
    assert _chat(env, "visitor-a", token=token).status_code == 200


# ── lead / escalation require the session ────────────────────────────────────


def test_lead_without_the_session_token_creates_no_lead(env):
    token = "G" * 43
    _seed(env, visitor_id="visitor-a", token=token)

    response = _lead(env, "visitor-a")

    assert response.status_code == 403
    assert env.leads == []
    assert env.logged == []


def test_lead_with_another_visitors_token_is_refused(env):
    _seed(env, visitor_id="visitor-a", token="H" * 43)
    _seed(env, visitor_id="visitor-b", token="I" * 43)

    response = _lead(env, "visitor-a", token="I" * 43)

    assert response.status_code == 403
    assert env.leads == []


def test_escalation_requires_the_matching_token(env):
    token = "J" * 43
    ws = _seed(env, visitor_id="visitor-a", token=token)
    escalate = {"public_key": KEY, "visitor_id": "visitor-a", "reason": "help"}

    refused = env.client.post("/api/widget/escalate", json=escalate)
    assert refused.status_code == 403
    assert not ws.escalated

    accepted = env.client.post(
        "/api/widget/escalate", json=escalate, headers={"X-Widget-Session": token}
    )
    assert accepted.status_code == 200
    assert ws.escalated is True


def test_authorized_lead_is_captured(env):
    token = "K" * 43
    _seed(env, visitor_id="visitor-a", token=token)

    response = _lead(env, "visitor-a", token=token)

    assert response.status_code == 200
    assert len(env.leads) == 1
    assert env.leads[0]["email"] == "a@example.com"


# ── rate limits by client IP and widget key ──────────────────────────────────


def test_rotated_visitor_ids_are_still_rate_limited(env, monkeypatch):
    monkeypatch.setenv("WIDGET_IP_RATE_LIMIT_PER_MIN", "2")

    statuses = [
        _chat(
            env, f"rotated-{i}", headers={"X-Forwarded-For": f"198.51.100.{i}"}
        ).status_code
        for i in range(4)
    ]

    # Forged X-Forwarded-For from an untrusted peer does not change the bucket.
    assert statuses == [200, 200, 429, 429]
    assert len(env.answered) == 2


def test_rejected_chat_creates_no_visitor_or_lead(env, monkeypatch):
    monkeypatch.setenv("WIDGET_IP_RATE_LIMIT_PER_MIN", "1")
    assert _chat(env, "first").status_code == 200
    before = len(env.session.added)

    response = _chat(env, "second-rotated-id")

    assert response.status_code == 429
    assert len(env.session.added) == before
    assert env.answered == ["hello"]


def test_rejected_lead_creates_no_lead(env, monkeypatch):
    monkeypatch.setenv("WIDGET_IP_RATE_LIMIT_PER_MIN", "2")
    tokens = {}
    for i in range(3):
        visitor = f"lead-visitor-{i}"
        tokens[visitor] = f"L{i}".ljust(43, "x")
        _seed(env, visitor_id=visitor, token=tokens[visitor])

    statuses = [_lead(env, v, token=tokens[v]).status_code for v in tokens]

    assert statuses == [200, 200, 429]
    assert len(env.leads) == 2


def test_event_and_feedback_are_ip_limited(env, monkeypatch):
    monkeypatch.setenv("WIDGET_IP_RATE_LIMIT_PER_MIN", "3")
    event_statuses = [
        env.client.post(
            "/api/widget/event",
            json={"public_key": KEY, "event": "opened", "visitor_id": f"e-{i}"},
        ).status_code
        for i in range(4)
    ]
    feedback_statuses = [
        env.client.post(
            "/api/widget/feedback",
            json={"public_key": KEY, "visitor_id": f"f-{i}", "rating": 5},
        ).status_code
        for i in range(4)
    ]

    assert event_statuses == [200, 200, 200, 429]
    assert feedback_statuses == [200, 200, 200, 429]


def test_event_is_linked_to_a_session_only_with_its_token(env):
    token = "M" * 43
    ws = _seed(env, visitor_id="visitor-a", token=token)
    payload = {
        "public_key": KEY,
        "event": "opened",
        "visitor_id": "visitor-a",
        "session_id": str(ws.id),
    }

    env.session.scalar_value = ws
    env.client.post("/api/widget/event", json=payload)
    env.client.post(
        "/api/widget/event", json=payload, headers={"X-Widget-Session": "wrong"}
    )
    env.client.post(
        "/api/widget/event", json=payload, headers={"X-Widget-Session": token}
    )

    assert [entry.session_id for entry in env.logged] == [None, None, ws.id]


def test_unknown_widget_key_is_rejected_before_any_write(env):
    response = env.client.post(
        "/api/widget/session", json={"public_key": "pk_unknown", "visitor_id": "x"}
    )
    assert response.status_code == 404
    assert env.session.added == []

"""Tenant security: lead and calls permissions, marketplace review exposure, webhook SSRF,
approval claims and send-retry safety.

No network and no database. Routes run through TestClient with scripted sessions,
DNS resolution is replaced with a fake resolver, and senders are recording fakes.
"""

from __future__ import annotations

import asyncio
import socket
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.api.calls import routes as calls_routes
from app.api.leads import routes as leads_routes
from app.api.marketplace import routes as marketplace_routes
from app.core.permissions import Permission, has_permission
from app.database.models.marketplace_review import MarketplaceReview
from app.database.models.workflow import RunStatus, RunStepStatus, StepType
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.middleware.project_context import ProjectContext, get_current_project
from app.services import authorization as authz
from app.services import workflow_engine as engine
from app.services.workflow_senders import OutboundNotConfigured

ORG = uuid.uuid4()
PROJECT = uuid.uuid4()
USER = uuid.uuid4()
LEAD_ID = uuid.uuid4()
DAYTIME = datetime(2026, 10, 17, 14, 0, tzinfo=timezone.utc)


# ───────────────────────── shared fakes ─────────────────────────


class _Rows:
    def __init__(self, items=(), rowcount=1):
        self._items = list(items)
        self.rowcount = rowcount

    def all(self):
        return list(self._items)


class FakeSession:
    """Scripted stand-in for AsyncSession. ``scalars`` results are consumed in order."""

    def __init__(self, scalars=()):
        self._scalars = list(scalars)
        self.statements = []
        self.commits = 0

    async def scalar(self, stmt):
        self.statements.append(stmt)
        return None

    async def scalars(self, stmt):
        self.statements.append(stmt)
        return _Rows(self._scalars.pop(0) if self._scalars else [])

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _Rows([])

    async def get(self, model, pk):
        return None

    def add(self, obj):
        pass

    async def flush(self):
        return None

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        return None

    async def refresh(self, obj):
        return None


def _sql(stmt) -> str:
    return str(
        stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


def _role_only_authorize(monkeypatch, recorded: list) -> None:
    """Real RBAC matrix, without the subscription lookups. Records each permission checked."""

    async def authorize(session, ctx, *, permission=None, **_):
        recorded.append(permission)
        if permission and not has_permission(ctx.membership_role, permission):
            raise HTTPException(
                403, f"Role '{ctx.membership_role}' lacks {permission}."
            )
        return SimpleNamespace(raise_for_denied=lambda: None)

    monkeypatch.setattr(authz, "authorize", authorize)


def _build_app(router, role: str, session: FakeSession) -> TestClient:
    async def _org():
        return OrgContext(
            user_id=USER, auth_subject="sub", organization_id=ORG, membership_role=role
        )

    async def _project():
        return ProjectContext(
            user_id=USER,
            organization_id=ORG,
            membership_role=role,
            project_id=PROJECT,
            project_slug="default",
            is_default_project=True,
        )

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_organization] = _org
    app.dependency_overrides[get_current_project] = _project
    app.dependency_overrides[get_db] = lambda: session
    return TestClient(app)


# ───────────────────────── permission matrix ─────────────────────────


def test_matrix_gives_members_calls_and_lead_writes_and_viewers_only_reads():
    assert has_permission("member", Permission.LEADS_WRITE)
    assert has_permission("member", Permission.CALLS_WRITE)
    assert has_permission("viewer", Permission.LEADS_READ)
    assert has_permission("viewer", Permission.CALLS_READ)
    assert not has_permission("viewer", Permission.LEADS_WRITE)
    assert not has_permission("viewer", Permission.CALLS_WRITE)


# ───────────────────────── leads: viewers cannot write ─────────────────────────


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/api/leads", {"name": "Ada", "email": "ada@example.com"}),
        ("patch", f"/api/leads/{LEAD_ID}", {"name": "Ada"}),
        ("delete", f"/api/leads/{LEAD_ID}", None),
    ],
)
def test_viewer_cannot_create_update_or_delete_a_lead(monkeypatch, method, path, body):
    recorded: list = []
    _role_only_authorize(monkeypatch, recorded)

    async def must_not_run(*_args, **_kwargs):
        raise AssertionError("a viewer reached the lead service")

    monkeypatch.setattr(leads_routes.lead_service, "create_lead", must_not_run)
    session = FakeSession()
    client = _build_app(leads_routes.router, "viewer", session)

    response = (
        client.request(method.upper(), path, json=body)
        if body
        else client.request(method.upper(), path)
    )

    assert response.status_code == 403
    assert Permission.LEADS_WRITE in recorded
    assert session.commits == 0


def test_viewer_can_still_read_leads(monkeypatch):
    recorded: list = []
    _role_only_authorize(monkeypatch, recorded)
    client = _build_app(leads_routes.router, "viewer", FakeSession(scalars=[[]]))

    response = client.get("/api/leads")

    assert response.status_code == 200
    assert response.json() == []
    assert recorded == [Permission.LEADS_READ]


# ───────────────────────── calls: permissions and viewer refusal ─────────────────────────


def test_viewer_cannot_create_or_pause_a_calling_campaign(monkeypatch):
    recorded: list = []
    _role_only_authorize(monkeypatch, recorded)
    client = _build_app(calls_routes.router, "viewer", FakeSession())

    created = client.post(
        "/api/calls/campaigns",
        json={"name": "Spring", "timezone": "UTC", "lead_status": "new"},
    )
    paused = client.post(f"/api/calls/campaigns/{uuid.uuid4()}/pause")

    assert created.status_code == 403
    assert paused.status_code == 403
    assert recorded == [Permission.CALLS_WRITE, Permission.CALLS_WRITE]


def test_calls_routes_check_calls_permissions_not_leads(monkeypatch):
    recorded: list = []
    _role_only_authorize(monkeypatch, recorded)
    client = _build_app(calls_routes.router, "admin", FakeSession(scalars=[[]]))

    client.get("/api/calls/campaigns")

    assert recorded == [Permission.CALLS_READ]
    assert Permission.LEADS_READ not in recorded


# ───────────────────────── marketplace reviews ─────────────────────────


def test_reviewer_label_never_shows_email_or_its_local_part():
    email_only = SimpleNamespace(full_name=None, email="ada.lovelace@example.com")
    assert marketplace_routes._author_name(email_only) == "Verified user"
    assert marketplace_routes._author_name(None) == "Verified user"
    assert (
        marketplace_routes._author_name(SimpleNamespace(full_name="ada@example.com"))
        == "Verified user"
    )
    assert (
        marketplace_routes._author_name(SimpleNamespace(full_name="  Ada  ")) == "Ada"
    )


def test_review_list_is_scoped_to_the_callers_organization_and_hides_emails(
    monkeypatch,
):
    monkeypatch.setattr(
        marketplace_routes.catalog, "get_listing", lambda slug: object()
    )
    review = SimpleNamespace(
        id=uuid.uuid4(),
        listing_slug="sales-agent",
        rating=5,
        title="Great",
        body="Works",
        user_id=USER,
        created_at=DAYTIME,
    )
    user = SimpleNamespace(id=USER, full_name=None, email="secret.person@example.com")
    session = FakeSession(scalars=[[review], [user]])
    ctx = OrgContext(
        user_id=uuid.uuid4(),
        auth_subject="sub",
        organization_id=ORG,
        membership_role="viewer",
    )

    result = asyncio.run(
        marketplace_routes.list_reviews("sales-agent", ctx=ctx, db=session)
    )

    assert str(ORG) in _sql(session.statements[0])
    assert result.count == 1
    assert result.reviews[0].author == "Verified user"
    assert "secret" not in result.model_dump_json()
    assert "example.com" not in result.model_dump_json()


def test_review_query_filters_by_organization_column():
    stmt_sql = _sql(
        select(MarketplaceReview).where(MarketplaceReview.organization_id == ORG)
    )
    assert str(ORG) in stmt_sql


# ───────────────────────── webhook SSRF ─────────────────────────


def _resolver(addresses):
    """Replace getaddrinfo so the host resolves to ``addresses``."""

    def fake_getaddrinfo(host, port, *args, **kwargs):
        results = []
        for addr in addresses:
            family = socket.AF_INET6 if ":" in addr else socket.AF_INET
            results.append((family, socket.SOCK_STREAM, 6, "", (addr, port or 443)))
        return results

    return fake_getaddrinfo


@pytest.fixture
def dev_env(monkeypatch):
    monkeypatch.setattr(engine.settings, "environment", "development")
    return monkeypatch


@pytest.mark.parametrize(
    ("url", "address"),
    [
        ("https://hooks.example.com/in", "127.0.0.1"),  # loopback
        ("https://hooks.example.com/in", "169.254.169.254"),  # cloud metadata
        ("https://hooks.example.com/in", "10.0.0.5"),  # RFC 1918
        ("https://hooks.example.com/in", "192.168.1.20"),  # RFC 1918
        ("https://hooks.example.com/in", "172.16.9.9"),  # RFC 1918
        ("https://hooks.example.com/in", "0.0.0.0"),  # unspecified
        ("https://hooks.example.com/in", "224.0.0.1"),  # multicast
        ("https://ipv6.example.com/in", "::1"),  # IPv6 loopback
        ("https://ipv6.example.com/in", "fe80::1"),  # IPv6 link-local
        ("https://ipv6.example.com/in", "fd00::5"),  # fc00::/7 unique local
        ("https://ipv6.example.com/in", "::ffff:127.0.0.1"),  # IPv4-mapped loopback
    ],
)
def test_webhook_refuses_internal_targets(monkeypatch, url, address):
    monkeypatch.setattr(socket, "getaddrinfo", _resolver([address]))
    with pytest.raises(ValueError):
        asyncio.run(engine._assert_public_webhook_target(url))


def test_webhook_refuses_a_host_if_any_resolved_address_is_internal(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _resolver(["93.184.216.34", "10.1.2.3"]))
    with pytest.raises(ValueError):
        asyncio.run(
            engine._assert_public_webhook_target("https://mixed.example.com/in")
        )


def test_webhook_allows_a_public_address(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _resolver(["93.184.216.34"]))
    asyncio.run(engine._assert_public_webhook_target("https://hooks.example.com/in"))


def test_webhook_refuses_plain_http_to_a_public_host(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _resolver(["93.184.216.34"]))
    with pytest.raises(ValueError, match="https"):
        asyncio.run(engine._assert_public_webhook_target("http://hooks.example.com/in"))


def test_webhook_allows_plain_http_to_localhost_only_in_development(
    dev_env, monkeypatch
):
    monkeypatch.setattr(socket, "getaddrinfo", _resolver(["127.0.0.1"]))
    asyncio.run(engine._assert_public_webhook_target("http://localhost:8080/in"))

    dev_env.setattr(engine.settings, "environment", "production")
    with pytest.raises(ValueError, match="https"):
        asyncio.run(engine._assert_public_webhook_target("http://localhost:8080/in"))


def test_webhook_step_does_not_call_an_internal_target(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _resolver(["169.254.169.254"]))

    class _NoNetwork:
        def __init__(self, *a, **k):
            raise AssertionError("the webhook was sent to an internal address")

    monkeypatch.setattr(httpx, "AsyncClient", _NoNetwork)
    with pytest.raises(ValueError):
        asyncio.run(engine._step_webhook({"url": "https://metadata.example.com/x"}, {}))


# ───────────────────────── approval claim ─────────────────────────


class _DbRow:
    """One workflow_runs row. The fake session applies the claim's WHERE clause to it."""

    def __init__(self, status):
        self.status = status


class _ClaimSession:
    def __init__(self, row: _DbRow):
        self.row = row
        self.commits = 0

    async def execute(self, stmt):
        # Yield so that two concurrent callers both reach their claim before either commits.
        await asyncio.sleep(0)
        sql = _sql(stmt)
        assert "UPDATE workflow_runs" in sql
        assert "status = 'awaiting_approval'" in sql
        if self.row.status == RunStatus.awaiting_approval:
            self.row.status = RunStatus.running
            return _Rows(rowcount=1)
        return _Rows(rowcount=0)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        return None


def test_two_concurrent_claims_on_one_run_have_one_winner():
    row = _DbRow(RunStatus.awaiting_approval)
    sessions = [_ClaimSession(row), _ClaimSession(row)]

    async def race():
        return await asyncio.gather(
            engine._claim_awaiting_approval(sessions[0], uuid.uuid4()),
            engine._claim_awaiting_approval(sessions[1], uuid.uuid4()),
        )

    results = asyncio.run(race())
    assert sorted(results) == [False, True]
    assert row.status == RunStatus.running


def test_two_concurrent_approvals_run_the_steps_after_the_pause_once(monkeypatch):
    run_id = uuid.uuid4()
    row = _DbRow(RunStatus.awaiting_approval)
    loop_calls: list[int] = []

    # Each caller loads its own copy, as two database sessions would. Sharing one object
    # would let the second caller see the first caller's in-memory changes.
    def fresh_load():
        run = SimpleNamespace(
            id=run_id,
            organization_id=ORG,
            status=RunStatus.awaiting_approval,
            output={},
            steps_completed=1,
            error_message=None,
            finished_at=None,
        )
        steps = [
            SimpleNamespace(
                status=RunStepStatus.awaiting_approval,
                output=None,
                finished_at=None,
                order_index=0,
                type=StepType.approval,
            ),
            SimpleNamespace(
                status=RunStepStatus.pending, order_index=1, type=StepType.notification
            ),
        ]
        workflow = SimpleNamespace(
            id=uuid.uuid4(), organization_id=ORG, run_count=0, success_count=0
        )
        return run, workflow, steps

    async def fake_load(session, _run_id):
        return fresh_load()

    async def fake_loop(session, workflow_, run_, steps_, context, *, start_index):
        loop_calls.append(start_index)

    class _Maker:
        def __call__(self):
            return self

        async def __aenter__(self):
            return _ClaimSession(row)

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(engine, "_maker", lambda: _Maker())
    monkeypatch.setattr(engine, "_load", fake_load)
    monkeypatch.setattr(engine, "_run_loop", fake_loop)
    monkeypatch.setattr(engine, "_audit_run", lambda *a, **k: None)
    monkeypatch.setattr(engine, "ensure_default_senders", lambda: None)

    async def double_click():
        await asyncio.gather(
            engine.resume_run(run_id, approved=True, note="first"),
            engine.resume_run(run_id, approved=True, note="second"),
        )

    asyncio.run(double_click())

    assert loop_calls == [1]  # exactly one caller continued past the approval step


# ───────────────────────── send retries ─────────────────────────


class _Sender:
    """Recording sender. Each entry in ``plan`` is an exception to raise, or None to succeed."""

    def __init__(self, plan):
        self.plan = list(plan)
        self.calls = 0
        self.delivered = []

    async def send(self, *, channel, recipient, text, organization_id, lead_id):
        self.calls += 1
        step = self.plan.pop(0) if self.plan else None
        if step is not None:
            raise step
        self.delivered.append(text)


@pytest.fixture
def send_env(monkeypatch):
    async def allowed(*_args, **_kwargs):
        return SimpleNamespace(allowed=True, reasons=[])

    monkeypatch.setattr(engine, "_consent_decision", allowed)
    monkeypatch.setattr(engine, "_utcnow", lambda: DAYTIME)
    yield monkeypatch
    engine.unregister_outbound_sender("email")


def _send_step(retry: int):
    return SimpleNamespace(
        name="Email the lead",
        type=StepType.notification,
        config={
            "action": "send_message",
            "channel": "email",
            "message": "Hello {{lead.name}}",
            "retry": retry,
            "retry_delay": 0,
        },
    )


def _lead():
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=ORG,
        conversation_id=None,
        name="Ada",
        email="ada@example.com",
        phone=None,
        company=None,
        intent=None,
        source="web",
        status=None,
        temperature=None,
        score=None,
        extra={},
        deleted_at=None,
    )


def test_a_step_that_failed_before_dispatch_is_retried_and_then_sent_once(send_env):
    sender = _Sender([OutboundNotConfigured("The email channel is reconnecting.")])
    engine.register_outbound_sender("email", sender)
    workflow = SimpleNamespace(organization_id=ORG)

    outcome = asyncio.run(
        engine._attempt_step(
            FakeSession(),
            workflow,
            _send_step(retry=2),
            _send_step(2).config,
            {},
            _lead(),
        )
    )

    assert outcome.status == "completed"
    assert sender.calls == 2
    assert len(sender.delivered) == 1
    assert outcome.output["attempts"] == 2
    assert outcome.output["dispatched"] is True


def test_a_send_that_may_have_been_delivered_is_never_sent_again(send_env):
    sender = _Sender([RuntimeError("connection reset after the request was written")])
    engine.register_outbound_sender("email", sender)
    workflow = SimpleNamespace(organization_id=ORG)

    outcome = asyncio.run(
        engine._attempt_step(
            FakeSession(),
            workflow,
            _send_step(retry=3),
            _send_step(3).config,
            {},
            _lead(),
        )
    )

    assert outcome.status == "failed"
    assert sender.calls == 1
    assert sender.delivered == []
    assert outcome.output["attempts"] == 1
    assert outcome.output["dispatched"] is True


def test_a_webhook_that_was_sent_is_not_retried(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _resolver(["93.184.216.34"]))
    calls = {"n": 0}

    class _Timeout:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None, **kwargs):
            # The send is pinned: url is the validated IP, with Host/SNI in kwargs.
            calls["n"] += 1
            raise httpx.ReadTimeout("no response after the body was sent")

    monkeypatch.setattr(httpx, "AsyncClient", _Timeout)
    step = SimpleNamespace(
        name="Notify partner",
        type=StepType.webhook,
        config={
            "url": "https://partner.example.com/hook",
            "retry": 3,
            "retry_delay": 0,
        },
    )
    outcome = asyncio.run(
        engine._attempt_step(
            FakeSession(),
            SimpleNamespace(organization_id=ORG),
            step,
            step.config,
            {},
            None,
        )
    )

    assert outcome.status == "failed"
    assert calls["n"] == 1

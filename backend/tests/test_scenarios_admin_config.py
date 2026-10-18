"""Admin configuration console scenarios: a super admin saves a draft, refusals for the wrong
role, a mistyped confirmation, a line break in a value, a missing encryption key, and
environment-scoped reads.

Drafts are never applied by saving, so the live value stays unchanged until publish. The
database, audit trail and encryption are replaced. Nothing is persisted.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin_config import routes as admin_routes
from app.database.models.user import UserRole
from app.database.session import get_db
from app.middleware import platform_context
from app.middleware.platform_context import PlatformContext
from app.services import config_console as console
from scenario_support import FakeSession, sql

KEY = "LOG_LEVEL"  # plain, console-managed, applies to local and production
REASON = "Raise verbosity while investigating the scenario ticket."


@pytest.fixture
def console_fakes(monkeypatch):
    """Replace persistence, audit and encryption. Records every write and refusal."""
    state = SimpleNamespace(
        drafts=[], live_writes=[], audits=[], rejected=[], active_rows=[], draft_rows=[]
    )

    async def fetch_rows(session, environment):
        return list(state.active_rows)

    async def fetch_drafts(session, environment):
        return list(state.draft_rows)

    async def upsert_draft(session, **kwargs):
        state.drafts.append(kwargs)

    async def upsert_live(session, **kwargs):
        state.live_writes.append(kwargs)

    async def no_flush(session):
        return None

    monkeypatch.setattr(console, "_fetch_rows", fetch_rows)
    monkeypatch.setattr(console, "_fetch_drafts", fetch_drafts)
    monkeypatch.setattr(console, "_upsert_draft", upsert_draft)
    monkeypatch.setattr(console, "_upsert_row", upsert_live)
    monkeypatch.setattr(console, "flush_pending", no_flush)
    monkeypatch.setattr(console, "encrypt", lambda value: f"enc::{len(value)}")
    monkeypatch.setattr(
        console, "_audit_draft", lambda ctx, key, env, **kw: state.audits.append(kw)
    )
    monkeypatch.setattr(
        console,
        "_audit_rejected",
        lambda ctx, *, environment, name, code: state.rejected.append(code),
    )
    return state


def _ctx() -> console.AuditContext:
    return console.AuditContext(
        actor_id="super-admin-scenario",
        actor_email="ops@example.test",
        ip=None,
        request_id="req-scenario-1",
    )


# ───────────────────────── happy path ─────────────────────────


@pytest.mark.smoke
async def test_super_admin_saves_a_draft_that_stays_inactive_until_published(
    console_fakes,
):
    session = FakeSession()

    result = await console.save_draft(
        session,
        ctx=_ctx(),
        environment="local",
        name=KEY,
        value="  DEBUG  ",
        confirm=KEY,
        reason=REASON,
    )

    assert result == {
        "name": KEY,
        "environment": "local",
        "status": "draft_saved",
        "active": False,
        "publish_required": True,
        "restart_required": False,
    }
    assert len(console_fakes.drafts) == 1
    assert console_fakes.drafts[0]["action"] == "set"
    assert console_fakes.drafts[0]["value_encrypted"] == "enc::5"
    assert console_fakes.live_writes == []
    assert session.commits == 1


# ───────────────────────── refusals ─────────────────────────


@pytest.mark.critical
@pytest.mark.parametrize(
    "role",
    [UserRole.admin.value, UserRole.manager.value, UserRole.user.value],
    ids=["org-admin", "manager", "member"],
)
def test_only_a_super_admin_can_reach_the_console(role, console_fakes):
    app = FastAPI()
    app.include_router(admin_routes.router)
    app.dependency_overrides[get_db] = lambda: FakeSession()

    async def as_role():
        return PlatformContext(
            user=SimpleNamespace(id="u-scenario", email="x@example.test"),
            auth_subject="scenario-sub",
            role=UserRole(role),
        )

    app.dependency_overrides[platform_context.get_current_platform_context] = as_role
    client = TestClient(app)

    response = client.put(
        f"/api/admin/config/{KEY}",
        json={
            "environment": "local",
            "value": "DEBUG",
            "confirm": KEY,
            "reason": REASON,
        },
    )

    assert response.status_code == 403
    assert console_fakes.drafts == []


@pytest.mark.critical
async def test_draft_is_refused_unless_the_exact_key_name_is_retyped(console_fakes):
    session = FakeSession()

    with pytest.raises(console.ConfigConsoleError) as refused:
        await console.save_draft(
            session,
            ctx=_ctx(),
            environment="local",
            name=KEY,
            value="DEBUG",
            confirm="log_level",
            reason=REASON,
        )

    assert refused.value.status == 400
    assert console_fakes.rejected == ["confirm_mismatch"]
    assert console_fakes.drafts == []
    assert session.commits == 0


@pytest.mark.critical
async def test_draft_without_a_real_reason_is_refused(console_fakes):
    with pytest.raises(console.ConfigConsoleError) as refused:
        await console.save_draft(
            FakeSession(),
            ctx=_ctx(),
            environment="local",
            name=KEY,
            value="DEBUG",
            confirm=KEY,
            reason="later",
        )

    assert refused.value.status == 400
    assert console_fakes.rejected == ["reason_length"]
    assert console_fakes.drafts == []


@pytest.mark.critical
async def test_value_with_a_line_break_is_refused_before_it_is_stored(console_fakes):
    with pytest.raises(console.ConfigConsoleError) as refused:
        await console.save_draft(
            FakeSession(),
            ctx=_ctx(),
            environment="local",
            name=KEY,
            value="DEBUG\nINJECTED=1",
            confirm=KEY,
            reason=REASON,
        )

    assert refused.value.status == 400
    assert console_fakes.rejected == ["invalid_value"]
    assert console_fakes.drafts == []


# ───────────────────────── external failure ─────────────────────────


@pytest.mark.regression
async def test_missing_encryption_key_stops_the_draft_with_a_503(
    monkeypatch, console_fakes
):
    def no_key(value):
        raise RuntimeError("scenario: no key material")

    monkeypatch.setattr(console, "encrypt", no_key)
    session = FakeSession()

    with pytest.raises(console.ConfigConsoleError) as failed:
        await console.save_draft(
            session,
            ctx=_ctx(),
            environment="local",
            name=KEY,
            value="DEBUG",
            confirm=KEY,
            reason=REASON,
        )

    assert failed.value.status == 503
    assert console_fakes.drafts == []
    assert session.commits == 0


# ───────────────────────── tenant isolation ─────────────────────────


@pytest.mark.critical
async def test_active_values_are_read_only_for_the_requested_environment():
    session = FakeSession()

    await console._fetch_rows(session, "production")

    statement = sql(session.statements[0])
    assert "'production'" in statement
    assert "'local'" not in statement


@pytest.mark.critical
async def test_draft_for_an_unknown_environment_is_refused_and_audited(console_fakes):
    with pytest.raises(console.ConfigConsoleError) as refused:
        await console.save_draft(
            FakeSession(),
            ctx=_ctx(),
            environment="staging",
            name=KEY,
            value="DEBUG",
            confirm=KEY,
            reason=REASON,
        )

    assert refused.value.status == 400
    assert console_fakes.rejected == ["bad_environment"]
    assert console_fakes.drafts == []

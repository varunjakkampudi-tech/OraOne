"""Outbound calling: campaign lifecycle, dial-time policy, Twilio status transitions and route guards.

Complements test_outbound_calls.py (planning rules, webhook signatures and the database-backed
queue). These tests use scripted in-memory sessions and mocked Twilio calls only.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
from fastapi import HTTPException
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.api.calls import routes as calls_routes
from app.core.permissions import has_permission
from app.database.models.call_campaign import AttemptStatus, CallAttempt, CampaignStatus
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.middleware.project_context import ProjectContext, get_current_project
from app.services import authorization as authz
from app.services.calls import campaign_service as svc
from app.services.calls.campaign_service import (
    CallingNotConfigured,
    CampaignError,
    DialError,
)

DAYTIME = datetime(2026, 10, 17, 14, 0, tzinfo=timezone.utc)
NIGHT = datetime(2026, 10, 17, 23, 30, tzinfo=timezone.utc)
PUBLIC_BASE = "https://api.example.test"
ACCOUNT_SID = "AC00000000000000000000000000000000"
AUTH_TOKEN = "calls-test-token"
TWILIO_NUMBER = "+15550001111"


def _cfg(**overrides):
    base = {
        "twilio_account_sid": ACCOUNT_SID,
        "twilio_auth_token": AUTH_TOKEN,
        "twilio_phone_number": TWILIO_NUMBER,
        "public_api_base_url": PUBLIC_BASE,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class _Rows:
    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return list(self._items)


class FakeSession:
    """Scripted stand-in for AsyncSession. Records statements and added objects."""

    def __init__(self, *, scalars=(), rows=(), objects=None):
        self._scalar = list(scalars)
        self._rows = list(rows)
        self._scalars = []
        self.objects = objects or {}
        self.statements = []
        self.added = []
        self.commits = 0

    async def scalar(self, stmt):
        self.statements.append(stmt)
        return self._scalar.pop(0) if self._scalar else None

    async def scalars(self, stmt):
        self.statements.append(stmt)
        return _Rows(self._scalars.pop(0) if self._scalars else [])

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _Rows(self._rows.pop(0) if self._rows else [])

    async def get(self, model, pk):
        return self.objects.get(pk)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        return None

    def queue_scalars(self, *results):
        self._scalars.extend(results)


def _attempt(**overrides):
    base = dict(
        id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        lead_id=uuid.uuid4(),
        status=AttemptStatus.calling,
        attempted_at=DAYTIME,
        outcome=None,
        duration_seconds=None,
        skip_reason=None,
        twilio_call_sid="CA123",
        created_at=DAYTIME,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _lead(**overrides):
    base = dict(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        phone="+14155550123",
        email=None,
        extra={"consent": "granted"},
        deleted_at=None,
        project_id=uuid.uuid4(),
        status="new",
        temperature="hot",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _sql(stmt) -> str:
    return str(
        stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


# ── configuration and validation ─────────────────────────────────────────────


def test_missing_configuration_names_every_missing_setting_without_echoing_secrets(
    monkeypatch,
):
    monkeypatch.setattr(
        svc,
        "get_channels_config",
        lambda: _cfg(twilio_auth_token="", twilio_phone_number=""),
    )
    missing = svc.missing_calling_config()
    assert "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN" in missing
    assert "TWILIO_PHONE_NUMBER" in missing
    assert svc.missing_calling_config() == missing  # stable

    with pytest.raises(CallingNotConfigured) as exc:
        svc.require_calling_config()
    assert exc.value.status_code == 503
    assert "TWILIO_PHONE_NUMBER" in exc.value.message
    assert ACCOUNT_SID not in exc.value.message


def test_fully_configured_calling_passes_the_gate(monkeypatch):
    monkeypatch.setattr(svc, "get_channels_config", lambda: _cfg())
    assert svc.missing_calling_config() == []
    svc.require_calling_config()  # does not raise


def test_public_url_is_required_for_calling(monkeypatch):
    monkeypatch.setattr(
        svc, "get_channels_config", lambda: _cfg(public_api_base_url="")
    )
    assert "PUBLIC_API_BASE_URL" in svc.missing_calling_config()


@pytest.mark.parametrize("name", ["Europe/London", "America/New_York", "UTC"])
def test_valid_iana_timezones_are_accepted(name):
    assert svc.validate_timezone(name) == name


@pytest.mark.parametrize("name", ["Mars/Olympus", "London", ""])
def test_unknown_timezone_is_refused_with_a_plain_message(name):
    with pytest.raises(CampaignError) as exc:
        svc.validate_timezone(name)
    assert exc.value.status_code == 422
    assert "IANA" in exc.value.message


@pytest.mark.parametrize(
    "status, expected",
    [
        (CampaignStatus.draft, True),
        (CampaignStatus.paused, True),
        (CampaignStatus.running, False),
        (CampaignStatus.completed, False),
    ],
)
def test_only_draft_or_paused_campaigns_can_start(status, expected):
    assert svc.can_start(status) is expected


@pytest.mark.parametrize(
    "status, expected",
    [
        (CampaignStatus.running, True),
        (CampaignStatus.draft, False),
        (CampaignStatus.paused, False),
        (CampaignStatus.completed, False),
    ],
)
def test_only_running_campaigns_can_pause(status, expected):
    assert svc.can_pause(status) is expected


# ── planning and campaign creation ───────────────────────────────────────────


def test_campaign_creation_with_no_matching_leads_is_refused_before_touching_the_database():
    session = FakeSession()
    with pytest.raises(CampaignError) as exc:
        asyncio.run(
            svc.create_campaign(
                session,
                organization_id=uuid.uuid4(),
                project_id=uuid.uuid4(),
                created_by=uuid.uuid4(),
                name="Spring",
                timezone_name="UTC",
                leads=[],
            )
        )
    assert exc.value.status_code == 422
    assert "No leads matched" in exc.value.message
    assert session.added == []


def test_campaign_with_an_unknown_timezone_is_refused_before_it_is_stored():
    session = FakeSession()
    with pytest.raises(CampaignError):
        asyncio.run(
            svc.create_campaign(
                session,
                organization_id=uuid.uuid4(),
                project_id=uuid.uuid4(),
                created_by=uuid.uuid4(),
                name="Spring",
                timezone_name="Mars/Olympus",
                leads=[_lead()],
            )
        )
    assert session.added == []


def test_planning_queues_allowed_leads_skips_others_and_ignores_foreign_and_duplicate_leads():
    org = uuid.uuid4()
    campaign = SimpleNamespace(id=uuid.uuid4(), organization_id=org, timezone="UTC")
    allowed = _lead(organization_id=org)
    no_consent = _lead(organization_id=org, extra={})
    foreign = _lead(organization_id=uuid.uuid4())
    session = FakeSession()

    summary = asyncio.run(
        svc.plan_attempts(
            session,
            campaign=campaign,
            leads=[allowed, allowed, no_consent, foreign],
            now=DAYTIME,
        )
    )

    assert summary == {"queued": 1, "skipped": 1}
    attempts = [o for o in session.added if isinstance(o, CallAttempt)]
    assert len(attempts) == 2
    by_lead = {a.lead_id: a for a in attempts}
    assert by_lead[allowed.id].status == AttemptStatus.queued
    assert by_lead[allowed.id].skip_reason is None
    assert by_lead[no_consent.id].status == AttemptStatus.skipped
    assert "consent" in by_lead[no_consent.id].skip_reason
    assert foreign.id not in by_lead


def test_lead_selection_is_scoped_to_organization_project_and_excludes_deleted_leads():
    org, project = uuid.uuid4(), uuid.uuid4()
    session = FakeSession()
    asyncio.run(
        svc.select_leads(
            session, organization_id=org, project_id=project, lead_status="new"
        )
    )
    sql = _sql(session.statements[0])
    assert str(org) in sql
    assert str(project) in sql
    assert "deleted_at IS NULL" in sql


def test_campaign_counts_group_by_status_and_skip_the_database_when_empty():
    session = FakeSession()
    assert asyncio.run(svc.campaign_counts(session, [])) == {}
    assert session.statements == []

    cid = uuid.uuid4()
    session = FakeSession(rows=[[(cid, "queued", 2), (cid, "failed", 1)]])
    counts = asyncio.run(svc.campaign_counts(session, [cid]))[cid]
    assert counts["queued"] == 2
    assert counts["failed"] == 1
    assert counts["completed"] == 0
    assert counts["total"] == 3


# ── dial-time policy and the queue ───────────────────────────────────────────


@pytest.fixture
def calling_configured(monkeypatch):
    monkeypatch.setattr(svc, "get_channels_config", lambda: _cfg())


@pytest.fixture
def dialer(monkeypatch):
    calls = []

    async def fake_place(attempt, *, to_number):
        calls.append({"attempt": attempt.id, "to": to_number})
        return "CA-NEW"

    monkeypatch.setattr(svc, "place_call", fake_place)
    return calls


def _running_campaign(org):
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=org,
        timezone="UTC",
        status=CampaignStatus.running,
    )


def test_dial_places_the_next_allowed_call_and_records_the_sid(
    calling_configured, dialer
):
    org = uuid.uuid4()
    campaign = _running_campaign(org)
    lead = _lead(organization_id=org)
    attempt = _attempt(
        status=AttemptStatus.queued,
        campaign_id=campaign.id,
        lead_id=lead.id,
        attempted_at=None,
        twilio_call_sid=None,
    )
    session = FakeSession(
        scalars=[campaign, attempt],
        objects={lead.id: lead},
    )
    session.queue_scalars([])  # no call in progress

    dialed = asyncio.run(svc.dial_next(session, campaign_id=campaign.id, now=DAYTIME))

    assert dialed is attempt
    assert attempt.status == AttemptStatus.calling
    assert attempt.attempted_at == DAYTIME
    assert attempt.twilio_call_sid == "CA-NEW"
    assert dialer == [{"attempt": attempt.id, "to": lead.phone}]
    assert session.commits >= 2  # the claim is recorded before Twilio is called


def test_quiet_hours_at_dial_time_skip_the_queued_lead_and_complete_the_campaign(
    calling_configured, dialer
):
    org = uuid.uuid4()
    campaign = _running_campaign(org)
    lead = _lead(organization_id=org)
    attempt = _attempt(
        status=AttemptStatus.queued,
        campaign_id=campaign.id,
        lead_id=lead.id,
        attempted_at=None,
        twilio_call_sid=None,
    )
    session = FakeSession(scalars=[campaign, attempt], objects={lead.id: lead})
    session.queue_scalars([])

    dialed = asyncio.run(svc.dial_next(session, campaign_id=campaign.id, now=NIGHT))

    assert dialed is None
    assert attempt.status == AttemptStatus.skipped
    assert "outside calling hours" in attempt.skip_reason
    assert campaign.status == CampaignStatus.completed
    assert dialer == []


def test_a_lead_from_another_organization_is_never_dialled(calling_configured, dialer):
    org = uuid.uuid4()
    campaign = _running_campaign(org)
    foreign_lead = _lead(organization_id=uuid.uuid4())
    attempt = _attempt(
        status=AttemptStatus.queued,
        campaign_id=campaign.id,
        lead_id=foreign_lead.id,
        attempted_at=None,
        twilio_call_sid=None,
    )
    session = FakeSession(
        scalars=[campaign, attempt], objects={foreign_lead.id: foreign_lead}
    )
    session.queue_scalars([])

    assert (
        asyncio.run(svc.dial_next(session, campaign_id=campaign.id, now=DAYTIME))
        is None
    )
    assert attempt.status == AttemptStatus.skipped
    assert "removed" in attempt.skip_reason
    assert dialer == []


def test_a_paused_campaign_never_dials(calling_configured, dialer):
    campaign = _running_campaign(uuid.uuid4())
    campaign.status = CampaignStatus.paused
    session = FakeSession(scalars=[campaign])

    assert (
        asyncio.run(svc.dial_next(session, campaign_id=campaign.id, now=DAYTIME))
        is None
    )
    assert dialer == []


def test_dial_is_refused_without_claiming_anything_when_calling_is_not_configured(
    monkeypatch, dialer
):
    monkeypatch.setattr(svc, "get_channels_config", lambda: _cfg(twilio_account_sid=""))
    session = FakeSession()

    with pytest.raises(CallingNotConfigured):
        asyncio.run(svc.dial_next(session, campaign_id=uuid.uuid4(), now=DAYTIME))
    assert session.statements == []
    assert dialer == []


def test_place_call_sends_the_attempt_url_and_status_callback_to_twilio(
    monkeypatch, calling_configured
):
    seen = {}

    class _Resp:
        status_code = 201

        def json(self):
            return {"sid": "CA-42"}

    async def fake_post(self, url, data=None, auth=None, **_):
        seen.update(url=url, data=data, auth=auth)
        return _Resp()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    attempt = _attempt()
    sid = asyncio.run(svc.place_call(attempt, to_number="+14155550123"))

    assert sid == "CA-42"
    assert (
        seen["url"]
        == f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Calls.json"
    )
    assert seen["auth"] == (ACCOUNT_SID, AUTH_TOKEN)
    assert seen["data"]["From"] == TWILIO_NUMBER
    assert seen["data"]["To"] == "+14155550123"
    assert seen["data"]["Url"] == f"{PUBLIC_BASE}/api/voice/twiml?attempt={attempt.id}"
    assert seen["data"]["StatusCallback"] == f"{PUBLIC_BASE}/api/voice/status"


@pytest.mark.parametrize("reply", ["no-json-sid", "empty-sid"])
def test_twilio_reply_without_a_call_id_is_a_dial_error(
    monkeypatch, calling_configured, reply
):
    class _Resp:
        status_code = 201

        def json(self):
            if reply == "no-json-sid":
                raise ValueError("not json")
            return {"sid": ""}

    async def fake_post(self, *a, **k):
        return _Resp()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    with pytest.raises(DialError) as exc:
        asyncio.run(svc.place_call(_attempt(), to_number="+14155550123"))
    assert exc.value.status_code == 502


def test_stale_calling_attempt_is_released_once_twilio_reports_it_ended(monkeypatch):
    # Changed: a stale attempt is no longer released on age alone; Twilio's status decides.
    async def fake_status(sid):
        return "completed"

    monkeypatch.setattr(svc, "fetch_call_status", fake_status)
    now = DAYTIME
    stale = _attempt(
        attempted_at=now
        - timedelta(minutes=svc.STALE_CALL_AFTER.total_seconds() / 60 + 1)
    )
    session = FakeSession()
    session.queue_scalars([stale])

    active = asyncio.run(svc._has_active_call(session, uuid.uuid4(), now))

    assert active is False
    assert stale.status == AttemptStatus.completed
    assert stale.outcome == "completed"


def test_fresh_calling_attempt_blocks_the_next_call():
    now = DAYTIME
    fresh = _attempt(attempted_at=now - timedelta(minutes=2))
    session = FakeSession()
    session.queue_scalars([fresh])

    assert asyncio.run(svc._has_active_call(session, uuid.uuid4(), now)) is True
    assert fresh.status == AttemptStatus.calling


def test_next_call_returns_nothing_while_a_call_is_in_progress():
    fresh = _attempt(attempted_at=DAYTIME)
    session = FakeSession()
    session.queue_scalars([fresh])
    session._scalar = [SimpleNamespace(status=AttemptStatus.queued)]

    async def run():
        import app.services.calls.campaign_service as module

        original = module._now
        module._now = lambda: DAYTIME
        try:
            return await svc.next_call(session, campaign_id=uuid.uuid4())
        finally:
            module._now = original

    assert asyncio.run(run()) is None


# ── Twilio status transitions ────────────────────────────────────────────────


def _status(session_attempt, status, duration=None):
    session = FakeSession(scalars=[])
    session._scalar = [session_attempt]
    transition = asyncio.run(
        svc.record_call_status(
            session, call_sid="CA123", call_status=status, duration=duration
        )
    )
    return transition


def test_in_progress_statuses_leave_the_attempt_calling():
    for status in ("queued", "initiated", "ringing", "in-progress"):
        attempt = _attempt(status=AttemptStatus.calling)
        assert _status(attempt, status) is None
        assert attempt.status == AttemptStatus.calling


def test_completed_call_is_recorded_with_duration_and_advances_the_queue_once():
    campaign_id = uuid.uuid4()
    attempt = _attempt(status=AttemptStatus.calling, campaign_id=campaign_id)
    transition = _status(attempt, "completed", duration="42")

    assert attempt.status == AttemptStatus.completed
    assert attempt.outcome == "completed"
    assert attempt.duration_seconds == 42
    assert transition is not None
    assert transition.campaign_id == campaign_id


@pytest.mark.parametrize("status", ["busy", "no-answer", "failed", "canceled"])
def test_unanswered_call_is_recorded_as_failed(status):
    attempt = _attempt(status=AttemptStatus.calling)
    transition = _status(attempt, status)
    assert attempt.status == AttemptStatus.failed
    assert attempt.outcome == status
    assert transition is not None


@pytest.mark.parametrize("duration", ["", None, "soon"])
def test_unusable_duration_is_stored_as_unknown_not_as_an_error(duration):
    attempt = _attempt(status=AttemptStatus.calling)
    _status(attempt, "completed", duration=duration)
    assert attempt.status == AttemptStatus.completed
    assert attempt.duration_seconds is None


def test_a_repeated_callback_for_a_finished_call_changes_nothing_and_advances_nothing():
    attempt = _attempt(
        status=AttemptStatus.completed, outcome="completed", duration_seconds=10
    )
    assert _status(attempt, "completed", duration="99") is None
    assert attempt.duration_seconds == 10


def test_callback_for_an_unknown_call_sid_is_ignored():
    session = FakeSession(scalars=[])
    session._scalar = [None]
    assert (
        asyncio.run(
            svc.record_call_status(session, call_sid="CA-none", call_status="completed")
        )
        is None
    )


# ── lifecycle route guards ───────────────────────────────────────────────────

ORG = uuid.uuid4()
PROJECT = uuid.uuid4()
USER = uuid.uuid4()


def _org_ctx(role="admin"):
    return OrgContext(
        user_id=USER, auth_subject="sub", organization_id=ORG, membership_role=role
    )


def _project_ctx(role="admin", org=ORG):
    return ProjectContext(
        user_id=USER,
        organization_id=org,
        membership_role=role,
        project_id=PROJECT,
        project_slug="default",
        is_default_project=True,
    )


def _campaign(status=CampaignStatus.draft, org=ORG):
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=org,
        project_id=PROJECT,
        name="Spring",
        status=status,
        timezone="UTC",
        created_by=USER,
        created_at=DAYTIME,
    )


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(calls_routes.audit_module, "audit", lambda *a, **k: None)

    async def role_only_authorize(session, ctx, *, permission=None, **_):
        # Real RBAC matrix, without the subscription lookups that would consume scripted rows.
        if permission and not has_permission(ctx.membership_role, permission):
            raise HTTPException(
                403, f"Role '{ctx.membership_role}' lacks {permission}."
            )
        return SimpleNamespace(raise_for_denied=lambda: None)

    monkeypatch.setattr(authz, "authorize", role_only_authorize)

    state = SimpleNamespace(role="admin", session=FakeSession(), org=ORG)

    async def _org():
        return _org_ctx(state.role)

    async def _project():
        return _project_ctx(state.role, state.org)

    app = FastAPI()
    app.include_router(calls_routes.router)
    app.dependency_overrides[get_current_organization] = _org
    app.dependency_overrides[get_current_project] = _project
    app.dependency_overrides[get_db] = lambda: state.session
    state.client = TestClient(app)
    return state


def test_starting_a_running_campaign_is_refused_with_409(api, monkeypatch):
    monkeypatch.setattr(svc, "get_channels_config", lambda: _cfg())
    api.session._scalar = [_campaign(CampaignStatus.running)]
    response = api.client.post(f"/api/calls/campaigns/{uuid.uuid4()}/start")
    assert response.status_code == 409
    assert (
        response.json()["detail"] == "Only a draft or paused campaign can be started."
    )


def test_pausing_a_draft_campaign_is_refused_with_409(api):
    api.session._scalar = [_campaign(CampaignStatus.draft)]
    response = api.client.post(f"/api/calls/campaigns/{uuid.uuid4()}/pause")
    assert response.status_code == 409


def test_starting_without_calling_configuration_fails_and_leaves_the_campaign_draft(
    api, monkeypatch
):
    monkeypatch.setattr(svc, "get_channels_config", lambda: _cfg(twilio_auth_token=""))
    campaign = _campaign(CampaignStatus.draft)
    api.session._scalar = [campaign]

    response = api.client.post(f"/api/calls/campaigns/{campaign.id}/start")

    assert response.status_code == 503
    assert campaign.status == CampaignStatus.draft
    assert api.session.commits == 0


def test_viewer_cannot_start_or_create_campaigns(api, monkeypatch):
    monkeypatch.setattr(svc, "get_channels_config", lambda: _cfg())
    api.role = "viewer"
    response = api.client.post(f"/api/calls/campaigns/{uuid.uuid4()}/start")
    assert response.status_code == 403


def test_campaign_lookup_is_scoped_to_the_callers_organization(api):
    api.session._scalar = [None]
    response = api.client.get(f"/api/calls/campaigns/{uuid.uuid4()}")
    assert response.status_code == 404
    sql = _sql(api.session.statements[0])
    assert str(ORG) in sql
    assert str(PROJECT) in sql


def test_creating_a_campaign_with_no_matching_leads_returns_422(api, monkeypatch):
    api.session._scalars = [[]]  # select_leads finds nothing
    response = api.client.post(
        "/api/calls/campaigns",
        json={"name": "Spring", "timezone": "UTC", "lead_status": "new"},
    )
    assert response.status_code == 422
    assert "No leads matched" in response.json()["detail"]


def test_creating_a_campaign_needs_a_lead_selection(api):
    response = api.client.post(
        "/api/calls/campaigns", json={"name": "Spring", "timezone": "UTC"}
    )
    assert response.status_code == 422


def test_invalid_attempt_status_filter_is_refused(api):
    api.session._scalar = [_campaign()]
    response = api.client.get(
        f"/api/calls/campaigns/{uuid.uuid4()}/attempts", params={"status": "exploded"}
    )
    assert response.status_code == 422
    assert "Invalid status" in response.json()["detail"]

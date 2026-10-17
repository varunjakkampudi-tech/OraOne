"""Outbound calling queue: planning rules, one call at a time, Twilio REST and callbacks.

No test places a real call or contacts Twilio. The Twilio REST client is replaced
with ``httpx.MockTransport`` and dialing is replaced with a fake in the DB tests.
Unit tests need no database. HTTP and queue tests need live Postgres and are
skipped when it is unreachable (same pattern as ``test_lead_import.py``).
"""

from __future__ import annotations

import asyncio
import base64
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from app.middleware.org_context import OrgContext
from app.services.calls import campaign_service as svc
from app.services.calls.campaign_service import CallingNotConfigured, DialError
from app.services.outreach_policy import Decision

# 14:00 UTC is daytime for every timezone used here; 23:30 UTC is quiet hours in UTC.
DAYTIME = datetime(2026, 10, 17, 14, 0, tzinfo=timezone.utc)
NIGHT = datetime(2026, 10, 17, 23, 30, tzinfo=timezone.utc)

PUBLIC_BASE = "https://api.example.test"
AUTH_TOKEN = "test-auth-token"
ACCOUNT_SID = "AC00000000000000000000000000000000"
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


def _lead(*, phone="+14155550123", **extra):
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        phone=phone,
        extra={"consent": "granted", **extra},
        deleted_at=None,
    )


# ───────────────────────── planning rules (no database) ─────────────────────────


@pytest.mark.parametrize(
    "lead, now, attempts, expected",
    [
        (_lead(opted_out=True), DAYTIME, 0, "asked not to be contacted"),
        (_lead(consent="denied"), DAYTIME, 0, "withdrew consent"),
        (_lead(suppressed=True), DAYTIME, 0, "do-not-contact"),
        (_lead(consent="unknown"), DAYTIME, 0, "do not have this contact's consent"),
        (
            SimpleNamespace(
                id=uuid.uuid4(), phone="+14155550123", extra={}, deleted_at=None
            ),
            DAYTIME,
            0,
            "consent",
        ),
        (_lead(), NIGHT, 0, "outside calling hours"),
        (_lead(), DAYTIME, 2, "today's limit of 2 attempts"),
        (_lead(phone="4155550123"), DAYTIME, 0, "country code starting with +"),
        (_lead(phone=None), DAYTIME, 0, "no phone number"),
    ],
)
def test_ineligible_lead_is_skipped_with_plain_reason(lead, now, attempts, expected):
    decision = svc.evaluate_lead(
        lead, attempts_last_24h=attempts, now=now, org_timezone="UTC"
    )
    assert decision.allowed is False
    assert any(expected in reason for reason in decision.reasons), decision.reasons


def test_consenting_reachable_lead_is_allowed_in_calling_hours():
    decision = svc.evaluate_lead(
        _lead(), attempts_last_24h=0, now=DAYTIME, org_timezone="UTC"
    )
    assert decision == Decision(True, [])


def test_lead_messaging_us_does_not_bypass_consent_for_calls():
    # The policy's reply window must not let an unconsented lead be cold-called.
    lead = _lead(consent="unknown")
    state = svc.contact_state_for(lead, attempts_last_24h=0)
    assert state.last_inbound_at is None
    assert (
        svc.evaluate_lead(
            lead, attempts_last_24h=0, now=DAYTIME, org_timezone="UTC"
        ).allowed
        is False
    )


# ───────────────────────── Twilio REST (mocked transport) ─────────────────────────


@pytest.fixture
def mock_twilio(monkeypatch):
    """Route every httpx.AsyncClient created by the service to a fake Twilio."""
    original = httpx.AsyncClient
    requests: list[httpx.Request] = []
    responses: list[httpx.Response] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return (
            responses.pop(0)
            if responses
            else httpx.Response(201, json={"sid": "CA" + "1" * 32})
        )

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return SimpleNamespace(requests=requests, responses=responses)


def _attempt():
    return SimpleNamespace(id=uuid.uuid4())


@pytest.mark.parametrize(
    "missing",
    [
        "twilio_account_sid",
        "twilio_auth_token",
        "twilio_phone_number",
        "public_api_base_url",
    ],
)
def test_place_call_refuses_without_config_and_never_calls_twilio(
    monkeypatch, mock_twilio, missing
):
    monkeypatch.setattr(svc, "get_channels_config", lambda: _cfg(**{missing: ""}))
    with pytest.raises(CallingNotConfigured) as exc:
        asyncio.run(svc.place_call(_attempt(), to_number="+14155550123"))
    assert exc.value.status_code == 503
    assert mock_twilio.requests == []
    assert "Calling is not configured" in exc.value.message


def test_place_call_posts_to_twilio_voice_with_basic_auth(monkeypatch, mock_twilio):

    monkeypatch.setattr(svc, "get_channels_config", lambda: _cfg())
    attempt = _attempt()
    sid = asyncio.run(svc.place_call(attempt, to_number="+14155550123"))

    assert sid == "CA" + "1" * 32
    assert len(mock_twilio.requests) == 1
    request = mock_twilio.requests[0]
    assert request.method == "POST"
    assert (
        str(request.url)
        == f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Calls.json"
    )
    expected_auth = (
        "Basic " + base64.b64encode(f"{ACCOUNT_SID}:{AUTH_TOKEN}".encode()).decode()
    )
    assert request.headers["authorization"] == expected_auth
    form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
    assert form["From"] == TWILIO_NUMBER
    assert form["To"] == "+14155550123"
    assert form["Url"] == f"{PUBLIC_BASE}/api/voice/twiml?attempt={attempt.id}"
    assert form["StatusCallback"] == f"{PUBLIC_BASE}/api/voice/status"


def test_place_call_rejects_non_e164_before_calling_twilio(monkeypatch, mock_twilio):

    monkeypatch.setattr(svc, "get_channels_config", lambda: _cfg())
    with pytest.raises(DialError):
        asyncio.run(svc.place_call(_attempt(), to_number="4155550123"))
    assert mock_twilio.requests == []


def test_twilio_refusal_is_reported_without_the_phone_number(monkeypatch, mock_twilio):

    monkeypatch.setattr(svc, "get_channels_config", lambda: _cfg())
    mock_twilio.responses.append(
        httpx.Response(400, json={"message": "Invalid To +14155550123"})
    )
    with pytest.raises(DialError) as exc:
        asyncio.run(svc.place_call(_attempt(), to_number="+14155550123"))
    assert exc.value.status_code == 400
    assert "14155550123" not in exc.value.message


# ───────────────────────── status callback signature (no database) ─────────────────────────


class _FakeSession:
    async def commit(self):
        pass

    async def rollback(self):
        pass


@pytest.fixture
def callback_client(monkeypatch):
    from app.api.calls import routes as calls_routes
    from app.database.session import get_db

    cfg = _cfg()
    monkeypatch.setattr(calls_routes, "get_channels_config", lambda: cfg)
    calls: list[dict] = []

    async def fake_record(session, *, call_sid, call_status, duration=None):
        calls.append(
            {"call_sid": call_sid, "call_status": call_status, "duration": duration}
        )
        return None

    monkeypatch.setattr(svc, "record_call_status", fake_record)

    async def fake_session():
        yield _FakeSession()

    app = FastAPI()
    app.include_router(calls_routes.callback_router)
    app.dependency_overrides[get_db] = fake_session
    return SimpleNamespace(client=TestClient(app), calls=calls, cfg=cfg)


STATUS_PATH = "/api/voice/status"
FORM = {"CallSid": "CA" + "2" * 32, "CallStatus": "completed", "CallDuration": "37"}


def _sign(params: dict, path: str = STATUS_PATH) -> str:
    return RequestValidator(AUTH_TOKEN).compute_signature(PUBLIC_BASE + path, params)


def test_status_callback_rejects_unsigned_request(callback_client):
    response = callback_client.client.post(STATUS_PATH, data=FORM)
    assert response.status_code == 401
    assert callback_client.calls == []


def test_status_callback_rejects_wrong_signature(callback_client):
    response = callback_client.client.post(
        STATUS_PATH, data=FORM, headers={"X-Twilio-Signature": "not-a-real-signature"}
    )
    assert response.status_code == 401
    assert callback_client.calls == []


def test_status_callback_rejects_tampered_body(callback_client):
    signature = _sign(FORM)
    tampered = {**FORM, "CallStatus": "in-progress"}
    response = callback_client.client.post(
        STATUS_PATH, data=tampered, headers={"X-Twilio-Signature": signature}
    )
    assert response.status_code == 401
    assert callback_client.calls == []


def test_status_callback_fails_closed_without_public_url(monkeypatch, callback_client):
    from app.api.calls import routes as calls_routes

    monkeypatch.setattr(
        calls_routes, "get_channels_config", lambda: _cfg(public_api_base_url="")
    )
    response = callback_client.client.post(
        STATUS_PATH, data=FORM, headers={"X-Twilio-Signature": _sign(FORM)}
    )
    assert response.status_code == 401
    assert callback_client.calls == []


def test_status_callback_accepts_correctly_signed_request(callback_client):
    response = callback_client.client.post(
        STATUS_PATH, data=FORM, headers={"X-Twilio-Signature": _sign(FORM)}
    )
    assert response.status_code == 204
    assert callback_client.calls == [
        {"call_sid": FORM["CallSid"], "call_status": "completed", "duration": "37"}
    ]


# ───────────────────────── database: queue, isolation, persistence ─────────────────────────


def _postgres_reachable() -> bool:
    import os

    import asyncpg

    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return False
    dsn = url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )

    async def _probe() -> bool:
        try:
            conn = await asyncio.wait_for(asyncpg.connect(dsn), timeout=3)
            await conn.close()
            return True
        except Exception:
            return False

    try:
        return asyncio.run(_probe())
    except RuntimeError:
        return False


REQUIRES_DB = pytest.mark.skipif(
    not _postgres_reachable(),
    reason="Postgres is not reachable from this host (private VPC, etc).",
)


@pytest_asyncio.fixture
async def db_session():
    from app.database import session as db_session_module
    from app.database.session import dispose_engine, init_engine

    await dispose_engine()
    init_engine()
    Maker = db_session_module.AsyncSessionLocal
    assert Maker is not None

    async with Maker() as s:
        yield s
        await s.rollback()

    await dispose_engine()


async def _seed_org(session, *, slug_hint: str):
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.organization_member import (
        MemberRole,
        MemberStatus,
        OrganizationMember,
    )
    from app.database.models.project import Project
    from app.database.models.user import User

    user = User(
        auth_subject=f"sub-{uuid.uuid4()}",
        email=f"{slug_hint}-{uuid.uuid4().hex[:8]}@x.com",
        full_name=slug_hint.title(),
    )
    session.add(user)
    await session.flush()
    org = Organization(
        name=f"{slug_hint.title()} Workspace",
        slug=f"{slug_hint}-{uuid.uuid4().hex[:8]}",
        plan=OrgPlan.free,
        owner_user_id=user.id,
    )
    session.add(org)
    await session.flush()
    session.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=MemberRole.owner,
            status=MemberStatus.active,
            joined_at=datetime.now(timezone.utc),
        )
    )
    project = Project(
        organization_id=org.id,
        name="Default",
        slug="default",
        is_default=True,
        created_by_user_id=user.id,
    )
    session.add(project)
    await session.flush()
    return user, org, project


async def _add_lead(
    session, *, org, project, phone="+14155550123", consent="granted", **extra
):
    from app.database.models.lead import Lead

    lead = Lead(
        organization_id=org.id,
        project_id=project.id,
        name=f"Lead {uuid.uuid4().hex[:6]}",
        phone=phone,
        source="import",
        extra={"consent": consent, **extra},
    )
    session.add(lead)
    await session.flush()
    return lead


async def _cleanup(session, *, org_ids, user_ids) -> None:
    from sqlalchemy import delete

    from app.database.models.call_campaign import CallAttempt, CallCampaign
    from app.database.models.lead import Lead
    from app.database.models.organization import Organization
    from app.database.models.organization_member import OrganizationMember
    from app.database.models.project import Project
    from app.database.models.user import User

    await session.rollback()
    await session.execute(
        delete(CallAttempt).where(CallAttempt.organization_id.in_(org_ids))
    )
    await session.execute(
        delete(CallCampaign).where(CallCampaign.organization_id.in_(org_ids))
    )
    await session.execute(delete(Lead).where(Lead.organization_id.in_(org_ids)))
    await session.execute(delete(Project).where(Project.organization_id.in_(org_ids)))
    await session.execute(
        delete(OrganizationMember).where(
            OrganizationMember.organization_id.in_(org_ids)
        )
    )
    await session.execute(delete(Organization).where(Organization.id.in_(org_ids)))
    await session.execute(delete(User).where(User.id.in_(user_ids)))
    await session.commit()


def _ctx(user, org) -> OrgContext:
    return OrgContext(
        user_id=user.id,
        auth_subject=f"sub-{org.id}",
        organization_id=org.id,
        membership_role="owner",
    )


@pytest.fixture
def calling_configured(monkeypatch):
    from app.api.calls import routes as calls_routes

    monkeypatch.setattr(svc, "get_channels_config", lambda: _cfg())
    monkeypatch.setattr(calls_routes, "get_channels_config", lambda: _cfg())
    monkeypatch.setattr(svc, "_now", lambda: DAYTIME)


@pytest.fixture
def fake_dialer(monkeypatch):
    """Replace the Twilio call with a fake that returns predictable call SIDs."""
    placed: list[str] = []

    async def fake_place_call(attempt, *, to_number):
        sid = f"CA{len(placed):032d}"
        placed.append(sid)
        return sid

    monkeypatch.setattr(svc, "place_call", fake_place_call)
    return placed


def _app():
    from app.api.calls import routes as calls_routes

    app = FastAPI()
    app.include_router(calls_routes.router)
    app.include_router(calls_routes.callback_router)
    return app


async def _real_session():
    """The API's own session dependency, so route handlers use the test database."""
    from app.database import session as db_session_module

    async with db_session_module.AsyncSessionLocal() as s:
        yield s


@REQUIRES_DB
@pytest.mark.asyncio
async def test_one_call_at_a_time_and_queue_drains_through_status_callbacks(
    db_session, calling_configured, fake_dialer
):
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select

    from app.database.models.call_campaign import CallAttempt, CallCampaign
    from app.database.session import get_db
    from app.middleware.org_context import get_current_organization

    user, org, project = await _seed_org(db_session, slug_hint="queue")
    user_id, org_id = user.id, org.id
    good_a = await _add_lead(db_session, org=org, project=project)
    good_b = await _add_lead(
        db_session, org=org, project=project, phone="+442079460958"
    )
    no_consent = await _add_lead(
        db_session, org=org, project=project, consent="unknown"
    )
    await db_session.commit()

    campaign = await svc.create_campaign(
        db_session,
        organization_id=org_id,
        project_id=project.id,
        created_by=user_id,
        name="Spring follow-up",
        timezone_name="UTC",
        leads=[good_a, good_b, no_consent],
        now=DAYTIME,
    )
    campaign.status = "running"
    campaign_id = campaign.id
    await db_session.commit()

    attempts = (
        await db_session.scalars(
            select(CallAttempt).where(CallAttempt.campaign_id == campaign_id)
        )
    ).all()
    by_status = sorted(a.status for a in attempts)
    assert by_status == ["queued", "queued", "skipped"]
    skipped = next(a for a in attempts if a.status == "skipped")
    assert "consent" in skipped.skip_reason

    async def _override() -> OrgContext:
        return _ctx(user, org)

    app = _app()
    app.dependency_overrides[get_current_organization] = _override
    app.dependency_overrides[get_db] = _real_session

    first = await svc.dial_next(db_session, campaign_id=campaign_id, now=DAYTIME)
    assert first is not None and first.status == "calling"
    assert len(fake_dialer) == 1

    # One active call per campaign: nothing else is dialed while the first is in progress.
    assert await svc.dial_next(db_session, campaign_id=campaign_id, now=DAYTIME) is None
    assert await svc.next_call(db_session, campaign_id=campaign_id) is None
    assert len(fake_dialer) == 1

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Unsigned status callbacks are refused and change nothing.
        r = await client.post(
            STATUS_PATH,
            data={"CallSid": first.twilio_call_sid, "CallStatus": "completed"},
        )
        assert r.status_code == 401

        # A signed callback for the first call ends it and places the second one.
        form = {
            "CallSid": first.twilio_call_sid,
            "CallStatus": "completed",
            "CallDuration": "42",
        }
        r = await client.post(
            STATUS_PATH,
            data=form,
            headers={"X-Twilio-Signature": _sign(form, STATUS_PATH)},
        )
        assert r.status_code == 204, r.text

        # Repeating the same callback must not dial anything else.
        r = await client.post(
            STATUS_PATH,
            data=form,
            headers={"X-Twilio-Signature": _sign(form, STATUS_PATH)},
        )
        assert r.status_code == 204
        assert len(fake_dialer) == 2

        db_session.expire_all()
        await db_session.refresh(first)
        assert first.status == "completed"
        assert first.duration_seconds == 42
        assert first.outcome == "completed"

        # Second call ends as no-answer: it is a failed attempt, and the queue completes.
        second_sid = await db_session.scalar(
            select(CallAttempt.twilio_call_sid).where(
                CallAttempt.campaign_id == campaign_id, CallAttempt.status == "calling"
            )
        )
        assert second_sid is not None
        form2 = {"CallSid": second_sid, "CallStatus": "no-answer"}
        r = await client.post(
            STATUS_PATH,
            data=form2,
            headers={"X-Twilio-Signature": _sign(form2, STATUS_PATH)},
        )
        assert r.status_code == 204

    db_session.expire_all()
    campaign = await db_session.scalar(
        select(CallCampaign).where(CallCampaign.id == campaign_id)
    )
    assert campaign.status == "completed"
    final = (
        await db_session.scalars(
            select(CallAttempt).where(CallAttempt.campaign_id == campaign_id)
        )
    ).all()
    assert sorted(a.status for a in final) == ["completed", "failed", "skipped"]
    failed = next(a for a in final if a.status == "failed")
    assert failed.outcome == "no-answer"

    await _cleanup(db_session, org_ids=[org_id], user_ids=[user_id])


@REQUIRES_DB
@pytest.mark.asyncio
async def test_failed_dial_is_recorded_and_does_not_stall_silently(
    db_session, calling_configured, monkeypatch
):
    from sqlalchemy import select

    from app.database.models.call_campaign import CallAttempt

    user, org, project = await _seed_org(db_session, slug_hint="dialfail")
    user_id, org_id = user.id, org.id
    lead = await _add_lead(db_session, org=org, project=project)
    await db_session.commit()
    campaign = await svc.create_campaign(
        db_session,
        organization_id=org_id,
        project_id=project.id,
        created_by=user_id,
        name="Failing",
        timezone_name="UTC",
        leads=[lead],
        now=DAYTIME,
    )
    campaign.status = "running"
    campaign_id = campaign.id
    await db_session.commit()

    async def refused(attempt, *, to_number):
        raise DialError(400, "Twilio refused the call (HTTP 400).")

    monkeypatch.setattr(svc, "place_call", refused)
    attempt = await svc.dial_next(db_session, campaign_id=campaign_id, now=DAYTIME)
    assert attempt.status == "failed"
    assert attempt.outcome == "dial_error_400"
    assert attempt.twilio_call_sid is None

    rows = (
        await db_session.scalars(
            select(CallAttempt).where(CallAttempt.campaign_id == campaign_id)
        )
    ).all()
    assert [r.status for r in rows] == ["failed"]
    await _cleanup(db_session, org_ids=[org_id], user_ids=[user_id])


@REQUIRES_DB
@pytest.mark.asyncio
async def test_campaign_reads_are_isolated_per_organization(
    db_session, calling_configured
):
    from httpx import ASGITransport, AsyncClient

    from app.database.session import get_db
    from app.middleware.org_context import get_current_organization

    user_a, org_a, project_a = await _seed_org(db_session, slug_hint="isoa")
    user_b, org_b, project_b = await _seed_org(db_session, slug_hint="isob")
    user_a_id, org_a_id, user_b_id, org_b_id = user_a.id, org_a.id, user_b.id, org_b.id
    lead_a = await _add_lead(db_session, org=org_a, project=project_a)
    await db_session.commit()

    current = {"ctx": _ctx(user_a, org_a)}

    async def _override() -> OrgContext:
        return current["ctx"]

    app = _app()
    app.dependency_overrides[get_current_organization] = _override
    app.dependency_overrides[get_db] = _real_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            created = await client.post(
                "/api/calls/campaigns",
                json={"name": "Org A only", "lead_ids": [str(lead_a.id)]},
            )
            assert created.status_code == 201, created.text
            body = created.json()
            campaign_id = body["id"]
            assert body["counts"]["queued"] == 1

            # Org B cannot see, read, or list Org A's campaign or its attempts.
            current["ctx"] = _ctx(user_b, org_b)
            assert (
                await client.get(f"/api/calls/campaigns/{campaign_id}")
            ).status_code == 404
            assert (
                await client.get(f"/api/calls/campaigns/{campaign_id}/attempts")
            ).status_code == 404
            assert (await client.get("/api/calls/campaigns")).json() == []

            # Org B cannot build a campaign from Org A's lead ids either.
            foreign = await client.post(
                "/api/calls/campaigns",
                json={"name": "Stolen leads", "lead_ids": [str(lead_a.id)]},
            )
            assert foreign.status_code == 422, foreign.text

            # Org A still sees its own campaign.
            current["ctx"] = _ctx(user_a, org_a)
            listing = await client.get("/api/calls/campaigns")
            assert [c["id"] for c in listing.json()] == [campaign_id]
    finally:
        await _cleanup(
            db_session, org_ids=[org_a_id, org_b_id], user_ids=[user_a_id, user_b_id]
        )

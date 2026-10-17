"""Outreach timing and consent: reply window, timezone fallback, live calls, import consent, OAuth nonce.

No test contacts Twilio or the network. Twilio REST is replaced with ``httpx.MockTransport``.
Database work is replaced with small fake sessions, so these tests need no Postgres.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest
from fastapi import Response

from app.api.integrations import routes
from app.database.models.call_campaign import AttemptStatus
from app.services import cache, oauth_service
from app.services import lead_import_service as imports
from app.services import workflow_triggers
from app.services.calls import campaign_service as svc
from app.services.outreach_policy import ContactState, check_outbound

# 14:00 UTC is daytime in London, Tokyo and New York. 23:30 UTC is quiet in London.
DAYTIME = datetime(2026, 10, 17, 14, 0, tzinfo=timezone.utc)
NIGHT = datetime(2026, 10, 17, 23, 30, tzinfo=timezone.utc)
# 05:00 UTC is 14:00 in Tokyo (daytime) but 05:00 in UTC (quiet).
EARLY_UTC = datetime(2026, 10, 17, 5, 0, tzinfo=timezone.utc)

ACCOUNT_SID = "AC00000000000000000000000000000000"
AUTH_TOKEN = "test-auth-token"
CALL_SID = "CA11111111111111111111111111111111"


# ───────────────────────────── reply window (finding 9) ─────────────────────────────


def test_reply_inside_24_hours_waives_consent_but_not_quiet_hours():
    inbound = DAYTIME - timedelta(hours=3)
    state = ContactState(
        consent="unknown", timezone="Europe/London", last_inbound_at=inbound
    )

    daytime = check_outbound(
        contact=state, channel="whatsapp", now=DAYTIME, is_reply=True
    )
    assert daytime.allowed is True

    late = NIGHT
    state_late = ContactState(
        consent="unknown",
        timezone="Europe/London",
        last_inbound_at=late - timedelta(minutes=5),
    )
    night = check_outbound(
        contact=state_late, channel="whatsapp", now=late, is_reply=True
    )
    assert night.allowed is False
    assert night.reasons == [
        "It is outside calling hours for this contact (08:00 to 21:00 local)."
    ]


def test_proactive_message_inside_24_hours_does_not_bypass_quiet_hours():
    # The customer wrote in the last 24 hours, but this send is not a reply.
    state = ContactState(
        consent="given",
        timezone="Europe/London",
        last_inbound_at=NIGHT - timedelta(hours=2),
    )
    decision = check_outbound(contact=state, channel="whatsapp", now=NIGHT)
    assert decision.allowed is False
    assert any("calling hours" in r for r in decision.reasons)


def test_proactive_message_inside_24_hours_without_consent_still_needs_consent():
    state = ContactState(
        consent="unknown",
        timezone="Europe/London",
        last_inbound_at=DAYTIME - timedelta(hours=2),
    )
    decision = check_outbound(contact=state, channel="sms", now=DAYTIME)
    assert decision.allowed is False
    assert any("consent" in r for r in decision.reasons)


def test_reply_does_not_bypass_the_attempt_cap():
    state = ContactState(
        consent="unknown",
        timezone="Europe/London",
        last_inbound_at=DAYTIME - timedelta(hours=1),
        attempts_last_24h=2,
    )
    decision = check_outbound(
        contact=state, channel="whatsapp", now=DAYTIME, is_reply=True
    )
    assert decision.allowed is False
    assert any("limit" in r for r in decision.reasons)


# ───────────────────────────── timezone fallback (finding 12) ─────────────────────────────


def _lead(*, phone="+14155550123", **extra):
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        phone=phone,
        extra={"consent": "granted", **extra},
        deleted_at=None,
    )


def test_lead_timezone_is_used_instead_of_the_campaign_timezone():
    # Campaign is UTC, where 05:00 is quiet. The lead is in Tokyo, where it is 14:00.
    lead = _lead(phone="+81312345678", timezone="Asia/Tokyo")
    decision = svc.evaluate_lead(
        lead, attempts_last_24h=0, now=EARLY_UTC, org_timezone="UTC"
    )
    assert decision.allowed is True, decision.reasons


def test_invalid_lead_timezone_falls_back_to_the_campaign_timezone_when_country_is_known():
    lead = _lead(phone="+442079460000", timezone="Not/AZone")
    decision = svc.evaluate_lead(
        lead, attempts_last_24h=0, now=NIGHT, org_timezone="UTC"
    )
    assert decision.allowed is False
    assert any("calling hours" in r for r in decision.reasons)


def test_no_lead_timezone_and_known_country_uses_the_campaign_timezone():
    decision = svc.evaluate_lead(
        _lead(), attempts_last_24h=0, now=DAYTIME, org_timezone="UTC"
    )
    assert decision == svc.Decision(True, [])


def test_unknown_timezone_and_unrecognised_country_code_is_not_dialed():
    lead = _lead(phone="+8001234567")
    decision = svc.evaluate_lead(
        lead, attempts_last_24h=0, now=DAYTIME, org_timezone="UTC"
    )
    assert decision.allowed is False
    assert any("cannot tell this contact's timezone" in r for r in decision.reasons)


def test_lead_timezone_rescues_an_unrecognised_country_code():
    lead = _lead(phone="+8001234567", timezone="Asia/Tokyo")
    decision = svc.evaluate_lead(
        lead, attempts_last_24h=0, now=EARLY_UTC, org_timezone="UTC"
    )
    assert decision.allowed is True, decision.reasons


# ───────────────────────────── live call not released early (finding 13) ─────────────────────────────


class _Result:
    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return list(self._items)


class _Session:
    def __init__(self, attempts):
        self.attempts = attempts

    async def scalars(self, _stmt):
        return _Result(self.attempts)

    async def flush(self):
        return None


def _calling(*, minutes_ago: float, sid=CALL_SID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=AttemptStatus.calling,
        attempted_at=DAYTIME - timedelta(minutes=minutes_ago),
        twilio_call_sid=sid,
        outcome=None,
    )


@pytest.fixture
def twilio(monkeypatch):
    """Install a Twilio REST handler. Call ``twilio(handler)``; ``twilio.seen`` lists requests."""
    seen: list[httpx.Request] = []
    real_client = httpx.AsyncClient

    def install(handler):
        def wrapped(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        monkeypatch.setattr(
            svc,
            "get_channels_config",
            lambda: SimpleNamespace(
                twilio_account_sid=ACCOUNT_SID,
                twilio_auth_token=AUTH_TOKEN,
                twilio_phone_number="+15550001111",
                public_api_base_url="https://api.example.test",
            ),
        )
        monkeypatch.setattr(
            svc.httpx,
            "AsyncClient",
            lambda *a, **k: real_client(
                *a, transport=httpx.MockTransport(wrapped), **k
            ),
        )

    install.seen = seen  # type: ignore[attr-defined]
    return install


def test_live_call_older_than_the_stale_limit_is_kept_while_twilio_says_in_progress(
    twilio,
):
    twilio(lambda req: httpx.Response(200, json={"status": "in-progress"}))
    attempt = _calling(minutes_ago=svc.STALE_CALL_AFTER.total_seconds() / 60 + 5)
    active = asyncio.run(
        svc._has_active_call(_Session([attempt]), uuid.uuid4(), DAYTIME)
    )
    assert active is True
    assert attempt.status == AttemptStatus.calling


def test_stale_call_is_kept_when_the_twilio_lookup_fails(twilio):
    twilio(lambda req: httpx.Response(500, json={"message": "boom"}))
    attempt = _calling(minutes_ago=45)
    active = asyncio.run(
        svc._has_active_call(_Session([attempt]), uuid.uuid4(), DAYTIME)
    )
    assert active is True
    assert attempt.status == AttemptStatus.calling


def test_stale_call_without_a_twilio_call_id_is_kept(twilio):
    twilio(lambda req: httpx.Response(200, json={"status": "completed"}))
    attempt = _calling(minutes_ago=45, sid=None)
    assert (
        asyncio.run(svc._has_active_call(_Session([attempt]), uuid.uuid4(), DAYTIME))
        is True
    )
    assert attempt.status == AttemptStatus.calling


def test_stale_call_is_released_when_twilio_says_it_completed(twilio):
    twilio(lambda req: httpx.Response(200, json={"status": "completed"}))
    attempt = _calling(minutes_ago=45)
    active = asyncio.run(
        svc._has_active_call(_Session([attempt]), uuid.uuid4(), DAYTIME)
    )
    assert active is False
    assert attempt.status == AttemptStatus.completed
    assert attempt.outcome == "completed"


def test_stale_call_is_released_when_twilio_has_no_such_call(twilio):
    twilio(lambda req: httpx.Response(404, json={"code": 20404}))
    attempt = _calling(minutes_ago=45)
    active = asyncio.run(
        svc._has_active_call(_Session([attempt]), uuid.uuid4(), DAYTIME)
    )
    assert active is False
    assert attempt.status == AttemptStatus.failed


def test_status_lookup_uses_the_calls_resource_with_account_auth(twilio):
    twilio(lambda req: httpx.Response(200, json={"status": "ringing"}))
    attempt = _calling(minutes_ago=45)
    asyncio.run(svc._has_active_call(_Session([attempt]), uuid.uuid4(), DAYTIME))
    (request,) = twilio.seen  # type: ignore[attr-defined]
    assert request.method == "GET"
    assert (
        request.url.path == f"/2010-04-01/Accounts/{ACCOUNT_SID}/Calls/{CALL_SID}.json"
    )
    assert request.headers["authorization"].startswith("Basic ")


# ───────────────────────────── imported consent (finding 17) ─────────────────────────────


class _FakeImportSession:
    def __init__(self):
        self.added: list = []

    def add_all(self, items):
        self.added.extend(items)

    async def flush(self):
        return None


@pytest.fixture
def no_lead_created_triggers(monkeypatch):
    async def _noop(*_a, **_k):
        return None

    monkeypatch.setattr(workflow_triggers, "fire_lead_created", _noop)


def _row(row_number, consent, phone):
    return imports.ParsedRow(
        row_number=row_number,
        status=imports.ROW_VALID,
        name=f"Contact {row_number}",
        phone=phone,
        consent=consent,
    )


def test_imported_yes_records_its_source_and_the_confirm_note(no_lead_created_triggers):
    parsed = imports.ParsedImport(
        file_name="leads.csv",
        file_format="csv",
        columns=[],
        rows=[_row(1, "granted", "+14155550123")],
    )
    session = _FakeImportSession()
    asyncio.run(
        imports.save_valid_rows(
            session,
            organization_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            parsed=parsed,
        )
    )
    (lead,) = session.added
    assert lead.extra["consent"] == "granted"
    assert lead.extra["consent_source"] == "import_csv"
    assert lead.extra["consent_note"] == "Imported consent, confirm the source"
    recorded = datetime.fromisoformat(lead.extra["consent_recorded_at"])
    assert recorded.tzinfo is not None


def test_imported_no_records_source_but_grants_nothing(no_lead_created_triggers):
    parsed = imports.ParsedImport(
        file_name="leads.csv",
        file_format="csv",
        columns=[],
        rows=[_row(1, "denied", "+14155550123")],
    )
    session = _FakeImportSession()
    asyncio.run(
        imports.save_valid_rows(
            session,
            organization_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            parsed=parsed,
        )
    )
    (lead,) = session.added
    assert lead.extra["consent"] == "denied"
    assert lead.extra["consent_source"] == "import_csv"
    assert "consent_note" not in lead.extra


def test_blank_import_consent_invents_no_source(no_lead_created_triggers):
    parsed = imports.ParsedImport(
        file_name="leads.csv",
        file_format="csv",
        columns=[],
        rows=[_row(1, "unknown", "+14155550123")],
    )
    session = _FakeImportSession()
    asyncio.run(
        imports.save_valid_rows(
            session,
            organization_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            parsed=parsed,
        )
    )
    (lead,) = session.added
    assert lead.extra["consent"] == "unknown"
    assert "consent_source" not in lead.extra
    assert "consent_recorded_at" not in lead.extra


# ───────────────────────────── OAuth nonce cookie (finding 16) ─────────────────────────────


@pytest.fixture
def oauth_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-outreach-timing-secret-32-bytes!")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("FRONTEND_URL", "http://frontend.test")
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    cache._namespaced_singletons.clear()


def _request(cookies):
    return SimpleNamespace(cookies=cookies)


def _state_with_nonce(nonce="browser-nonce"):
    return routes.issue_oauth_state(
        provider="google_drive",
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        nonce_hash=routes._nonce_hash(nonce),
    )


def test_oauth_callback_without_the_nonce_cookie_is_refused_before_any_exchange(
    monkeypatch, oauth_env
):
    def _no_exchange(*_a, **_k):
        raise AssertionError("code must not be exchanged without the nonce cookie")

    monkeypatch.setattr(oauth_service, "complete_connect", _no_exchange)
    response = asyncio.run(
        routes.google_oauth_callback(
            request=_request({}),
            code="auth-code",
            state=_state_with_nonce(),
            error=None,
            session=None,
        )
    )
    assert (
        response.headers["location"]
        == "http://frontend.test/studio/integrations?error=invalid_state"
    )


def test_oauth_callback_with_a_different_nonce_cookie_is_refused(
    monkeypatch, oauth_env
):
    def _no_exchange(*_a, **_k):
        raise AssertionError("code must not be exchanged with a mismatched nonce")

    monkeypatch.setattr(oauth_service, "complete_connect", _no_exchange)
    response = asyncio.run(
        routes.google_oauth_callback(
            request=_request({routes._NONCE_COOKIE: "someone-else"}),
            code="auth-code",
            state=_state_with_nonce(),
            error=None,
            session=None,
        )
    )
    assert response.headers["location"].endswith("?error=invalid_state")


def test_oauth_state_without_a_nonce_binding_is_refused(monkeypatch, oauth_env):
    def _no_exchange(*_a, **_k):
        raise AssertionError("an unbound state must not reach the exchange")

    monkeypatch.setattr(oauth_service, "complete_connect", _no_exchange)
    unbound = routes.issue_oauth_state(
        provider="google_drive", organization_id=uuid.uuid4(), user_id=uuid.uuid4()
    )
    response = asyncio.run(
        routes.google_oauth_callback(
            request=_request({routes._NONCE_COOKIE: "anything"}),
            code="auth-code",
            state=unbound,
            error=None,
            session=None,
        )
    )
    assert response.headers["location"].endswith("?error=invalid_state")


def test_oauth_callback_with_the_matching_nonce_cookie_reaches_the_provider_check(
    monkeypatch, oauth_env
):
    def _no_exchange(*_a, **_k):
        raise AssertionError("no credentials, so the exchange must not run")

    monkeypatch.setattr(oauth_service, "complete_connect", _no_exchange)
    response = asyncio.run(
        routes.google_oauth_callback(
            request=_request({routes._NONCE_COOKIE: "browser-nonce"}),
            code="auth-code",
            state=_state_with_nonce("browser-nonce"),
            error=None,
            session=None,
        )
    )
    # Past the nonce check: without credentials the flow stops at the configuration check.
    assert response.headers["location"].endswith("?error=not_configured")


def test_connect_sets_an_httponly_lax_nonce_cookie_on_the_authorize_leg(
    monkeypatch, oauth_env
):
    from app.api.integrations.routes import connect_integration

    monkeypatch.setattr(oauth_service, "is_configured", lambda provider: True)
    monkeypatch.setattr(
        oauth_service,
        "build_authorize_url",
        lambda provider, *, state: "https://accounts.example/auth",
    )

    payload = SimpleNamespace(
        provider="google_drive", code=None, config=None, mock=False
    )
    pctx = SimpleNamespace(
        org=SimpleNamespace(organization_id=uuid.uuid4(), user_id=uuid.uuid4()),
        project_id=uuid.uuid4(),
    )
    response = Response()
    result = asyncio.run(
        connect_integration(payload, response, pctx=pctx, session=None)
    )
    assert result.authorize_url == "https://accounts.example/auth"
    cookie = response.headers["set-cookie"]
    assert f"{routes._NONCE_COOKIE}=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert f"Path={routes._NONCE_COOKIE_PATH}" in cookie

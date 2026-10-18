"""Outbound calling scenarios: consent and calling hours, the Twilio dialer, outages, and
campaign isolation by organization and project.

Twilio is replaced with a recording fake. The campaign clock is pinned to DAYTIME.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import httpx
import pytest

from app.api.calls import routes as calls_routes
from app.core.permissions import Permission
from app.services.calls import campaign_service as svc
from scenario_support import (
    DAYTIME,
    ORG_A,
    ORG_B,
    PROJECT_A,
    QUIET_HOURS,
    FakeSession,
    channels_config,
    org_app,
    record_permissions,
    sql,
)

TWILIO_CONFIG = dict(
    twilio_account_sid="ACscenario0000000000000000000000",
    twilio_auth_token="scenario-twilio-token",
    twilio_phone_number="+15550001111",
    public_api_base_url="https://api.example.test",
    twilio_configured=True,
)


def _lead(extra: dict | None = None, phone: str | None = "+447700900123"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=ORG_A,
        phone=phone,
        email="lead@example.test",
        extra={"consent": "granted"} if extra is None else extra,
    )


@pytest.fixture(autouse=True)
def pinned_clock(monkeypatch):
    monkeypatch.setattr(svc, "_now", lambda: DAYTIME)


@pytest.fixture
def twilio(monkeypatch):
    cfg = channels_config(**TWILIO_CONFIG)
    monkeypatch.setattr(svc, "get_channels_config", lambda: cfg)
    return cfg


# ───────────────────────── happy path ─────────────────────────


@pytest.mark.smoke
async def test_consented_lead_in_calling_hours_is_dialed_and_twilio_returns_a_call_id(
    monkeypatch, twilio
):
    decision = svc.evaluate_lead(
        _lead(),
        attempts_last_24h=0,
        now=DAYTIME,
        org_timezone="Europe/London",
    )
    assert decision.allowed
    assert decision.reasons == []

    seen: dict = {}

    async def create_call(self, url, data=None, auth=None, **_):
        seen.update(url=url, data=data, auth=auth)
        return SimpleNamespace(status_code=201, json=lambda: {"sid": "CA0001"})

    monkeypatch.setattr(httpx.AsyncClient, "post", create_call)
    attempt = SimpleNamespace(id=uuid.uuid4())

    sid = await svc.place_call(attempt, to_number="+447700900123")

    assert sid == "CA0001"
    assert seen["url"].endswith(
        f"/Accounts/{TWILIO_CONFIG['twilio_account_sid']}/Calls.json"
    )
    assert seen["auth"] == (
        TWILIO_CONFIG["twilio_account_sid"],
        TWILIO_CONFIG["twilio_auth_token"],
    )
    assert seen["data"]["To"] == "+447700900123"
    assert seen["data"]["From"] == "+15550001111"
    assert seen["data"]["Url"].endswith(f"/api/voice/twiml?attempt={attempt.id}")
    assert seen["data"]["StatusCallback"] == "https://api.example.test/api/voice/status"


# ───────────────────────── refusals ─────────────────────────


@pytest.mark.critical
@pytest.mark.parametrize(
    ("extra", "now", "reason_fragment"),
    [
        ({"consent": "unknown"}, DAYTIME, "consent"),
        ({"consent": "denied"}, DAYTIME, "consent"),
        (
            {"consent": "granted", "opted_out": True},
            DAYTIME,
            "asked not to be contacted",
        ),
        ({"consent": "granted"}, QUIET_HOURS, "outside calling hours"),
    ],
    ids=["no-consent", "consent-denied", "opted-out", "quiet-hours"],
)
def test_calls_are_refused_without_consent_after_opt_out_or_in_quiet_hours(
    extra, now, reason_fragment
):
    decision = svc.evaluate_lead(
        _lead(extra=extra), attempts_last_24h=0, now=now, org_timezone="UTC"
    )

    assert not decision.allowed
    assert any(reason_fragment in reason for reason in decision.reasons)


@pytest.mark.critical
def test_lead_on_the_do_not_contact_list_is_refused():
    decision = svc.evaluate_lead(
        _lead(),
        attempts_last_24h=0,
        now=DAYTIME,
        org_timezone="UTC",
        suppressed=True,
    )

    assert not decision.allowed
    assert any("do-not-contact" in reason for reason in decision.reasons)


@pytest.mark.critical
def test_viewer_cannot_start_a_calling_campaign(monkeypatch):
    recorded: list = []
    record_permissions(monkeypatch, recorded)

    async def must_not_dial(*_args, **_kwargs):
        raise AssertionError("a viewer reached the dialer")

    monkeypatch.setattr(svc, "dial_next", must_not_dial)
    session = FakeSession()
    client = org_app(calls_routes.router, role="viewer", session=session)

    response = client.post(f"/api/calls/campaigns/{uuid.uuid4()}/start")

    assert response.status_code == 403
    assert Permission.CALLS_WRITE in recorded
    assert session.commits == 0


@pytest.mark.critical
async def test_dialer_refuses_without_twilio_configuration_and_never_calls_twilio(
    monkeypatch,
):
    monkeypatch.setattr(svc, "get_channels_config", lambda: channels_config())
    calls: list = []

    async def record(self, url, **_):
        calls.append(url)
        raise AssertionError("Twilio must not be contacted without configuration")

    monkeypatch.setattr(httpx.AsyncClient, "post", record)

    with pytest.raises(svc.CallingNotConfigured) as refused:
        await svc.place_call(
            SimpleNamespace(id=uuid.uuid4()), to_number="+447700900123"
        )

    assert refused.value.status_code == 503
    assert calls == []


# ───────────────────────── external failure ─────────────────────────


@pytest.mark.regression
@pytest.mark.parametrize(
    ("failure", "expected_status"),
    [("twilio-503", 503), ("transport-error", 502)],
    ids=["twilio-rejects", "twilio-unreachable"],
)
async def test_twilio_failure_surfaces_as_a_dial_error_and_no_sid_is_recorded(
    monkeypatch, twilio, failure, expected_status
):
    async def failing(self, url, **_):
        if failure == "transport-error":
            raise httpx.ConnectError("scenario outage")
        return SimpleNamespace(status_code=503, json=lambda: {})

    monkeypatch.setattr(httpx.AsyncClient, "post", failing)

    with pytest.raises(svc.DialError) as failed:
        await svc.place_call(
            SimpleNamespace(id=uuid.uuid4()), to_number="+447700900123"
        )

    assert failed.value.status_code == expected_status


@pytest.mark.regression
async def test_twilio_status_lookup_failure_is_not_read_as_a_finished_call(
    monkeypatch, twilio
):
    def _unreadable_json():
        raise ValueError("not json")

    async def unreadable(self, url, **_):
        return SimpleNamespace(status_code=200, json=_unreadable_json)

    monkeypatch.setattr(httpx.AsyncClient, "get", unreadable)

    with pytest.raises(svc.CallLookupError):
        await svc.fetch_call_status("CA0001")


# ───────────────────────── tenant isolation ─────────────────────────


@pytest.mark.critical
@pytest.mark.parametrize(
    ("method", "suffix"),
    [("get", ""), ("post", "/start")],
    ids=["read", "start"],
)
def test_campaign_lookup_is_scoped_to_the_callers_org_and_project(
    monkeypatch, method, suffix
):
    recorded: list = []
    record_permissions(monkeypatch, recorded)
    session = FakeSession()  # no row matches, as for a campaign in another tenant
    client = org_app(calls_routes.router, role="member", session=session, org_id=ORG_A)
    campaign_id = uuid.uuid4()

    response = getattr(client, method)(f"/api/calls/campaigns/{campaign_id}{suffix}")

    assert response.status_code == 404
    statement = sql(session.statements[0])
    assert str(ORG_A) in statement
    assert str(PROJECT_A) in statement
    assert str(ORG_B) not in statement
    assert str(campaign_id) in statement

"""Marketing campaigns: consent planning, honest sending, the double-send guard, roles, isolation and unsubscribe.

Scripted in-memory sessions and fake senders only. No test opens a socket or reaches a provider.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.api.marketing import routes as marketing_routes
from app.core.config import settings
from app.core.permissions import has_permission
from app.database.models.marketing import (
    MarketingCampaign,
    MarketingCampaignStatus,
    MarketingRecipient,
    MarketingRecipientStatus,
)
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.middleware.project_context import ProjectContext, get_current_project
from app.services import authorization as authz
from app.services import contact_policy_service
from app.services.channels import adapters
from app.services.channels.config import ChannelsConfig
from app.services.marketing import campaigns as svc
from app.services.marketing import unsubscribe as unsub
from app.services.marketing.campaigns import (
    PROVIDER_REFUSED_REASON,
    UNSUBSCRIBE_UNAVAILABLE_REASON,
    CampaignConflict,
    CampaignError,
    CampaignNotFound,
)
from app.services.marketing.unsubscribe import InvalidUnsubscribeToken
from app.services.workflow_senders import ChannelOutboundSender, OutboundNotConfigured

DAYTIME = datetime(2026, 10, 17, 14, 0, tzinfo=timezone.utc)
NIGHT = datetime(2026, 10, 17, 23, 30, tzinfo=timezone.utc)
PUBLIC_BASE = "https://api.example.test"
TEST_SECRET = "marketing-test-secret-0123456789abcdefghijklmnop"

ORG = uuid.uuid4()
OTHER_ORG = uuid.uuid4()
PROJECT = uuid.uuid4()
USER = uuid.uuid4()


# ───────────────────────────── fixtures and fakes ─────────────────────────────


@pytest.fixture(autouse=True)
def _fixed_secret(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret_key", TEST_SECRET)


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    import socket

    def refuse(self, address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) else str(address)
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError("network access is not allowed in this test")
        return real_connect(self, address, *args, **kwargs)

    real_connect = socket.socket.connect
    monkeypatch.setattr(socket.socket, "connect", refuse)


class _Rows:
    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return list(self._items)


class ScriptedSession:
    """Records statements and returns queued results in order. Missing results are empty."""

    def __init__(self, *, scalar=(), scalars=(), execute=()):
        self._scalar = list(scalar)
        self._scalars = list(scalars)
        self._execute = list(execute)
        self.statements: list = []
        self.added: list = []
        self.commits = 0
        self.rollbacks = 0
        # Objects handed out by queries, so that session.get returns the same instances.
        self.objects: list = []

    def _remember(self, items):
        for item in items:
            if isinstance(item, tuple):
                self.objects.extend(item)
            else:
                self.objects.append(item)

    async def scalar(self, stmt):
        self.statements.append(stmt)
        return self._scalar.pop(0) if self._scalar else None

    async def scalars(self, stmt):
        self.statements.append(stmt)
        rows = self._scalars.pop(0) if self._scalars else []
        self._remember(rows)
        return _Rows(rows)

    async def execute(self, stmt):
        self.statements.append(stmt)
        rows = self._execute.pop(0) if self._execute else []
        self._remember(rows)
        return _Rows(rows)

    async def get(self, model, pk):
        return next(
            (obj for obj in self.objects if getattr(obj, "id", None) == pk), None
        )

    async def refresh(self, obj):
        return None

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class _SessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc):
        return False


class SpySender:
    def __init__(self, *, error: Exception | None = None):
        self.calls: list[dict] = []
        self._error = error

    async def send(self, *, channel, recipient, text, organization_id, lead_id):
        self.calls.append(
            {
                "channel": channel,
                "recipient": recipient,
                "text": text,
                "lead_id": lead_id,
            }
        )
        if self._error is not None:
            raise self._error
        return {"provider": "fake"}


def _lead(**overrides):
    base = dict(
        id=uuid.uuid4(),
        organization_id=ORG,
        project_id=PROJECT,
        name="Jane Doe",
        email="Jane.Doe@Example.com",
        phone="+14155550123",
        extra={"consent": "granted"},
        deleted_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _campaign(channel="email", status=MarketingCampaignStatus.draft, org=ORG):
    return MarketingCampaign(
        id=uuid.uuid4(),
        organization_id=org,
        project_id=PROJECT,
        name="Spring offer",
        channel=channel,
        subject="Hello" if channel == "email" else None,
        body="Our spring offer is live.",
        status=status,
        created_by=USER,
        created_at=DAYTIME,
        sent_count=0,
        skipped_count=0,
        failed_count=0,
    )


def _recipient(campaign, lead, status=MarketingRecipientStatus.queued):
    return MarketingRecipient(
        id=uuid.uuid4(),
        organization_id=campaign.organization_id,
        campaign_id=campaign.id,
        lead_id=lead.id,
        status=status,
        skip_reason=None,
        failure_reason=None,
        sent_at=None,
    )


def _sql(stmt) -> str:
    return str(
        stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


@pytest.fixture
def no_history(monkeypatch):
    """No prior sends in the last 24 hours and no do-not-contact hits, unless a test overrides."""

    async def attempts(session, *, organization_id, lead_ids, now):
        return {}

    async def suppressed(session, *, organization_id, leads, channel):
        return set()

    monkeypatch.setattr(svc, "attempts_last_24h", attempts)
    monkeypatch.setattr(contact_policy_service, "suppressed_lead_ids", suppressed)


def _set_suppressed(monkeypatch, lead_ids):
    async def suppressed(session, *, organization_id, leads, channel):
        return {lead.id for lead in leads if lead.id in lead_ids}

    monkeypatch.setattr(contact_policy_service, "suppressed_lead_ids", suppressed)


def _set_attempts(monkeypatch, counts):
    async def attempts(session, *, organization_id, lead_ids, now):
        return dict(counts)

    monkeypatch.setattr(svc, "attempts_last_24h", attempts)


# ───────────────────────────── planning (consent and policy) ─────────────────────────────


async def _plan(leads, *, channel="email", now=DAYTIME, subject="Hello"):
    session = ScriptedSession(scalars=[list(leads)])
    campaign = await svc.create_campaign(
        session,
        organization_id=ORG,
        project_id=PROJECT,
        created_by=USER,
        name="Spring",
        channel=channel,
        subject=subject,
        body="Our spring offer.",
        lead_ids=[lead.id for lead in leads],
        now=now,
    )
    recipients = [obj for obj in session.added if isinstance(obj, MarketingRecipient)]
    return campaign, recipients


@pytest.mark.asyncio
async def test_consent_given_is_queued(no_history):
    lead = _lead()
    _, [recipient] = await _plan([lead])
    assert recipient.status == MarketingRecipientStatus.queued
    assert recipient.skip_reason is None


@pytest.mark.asyncio
async def test_unknown_consent_is_skipped_with_plain_reason(no_history):
    lead = _lead(extra={})
    campaign, [recipient] = await _plan([lead])
    assert recipient.status == MarketingRecipientStatus.skipped
    assert (
        recipient.skip_reason == "We do not have this contact's consent to reach out."
    )
    assert campaign.skipped_count == 1


@pytest.mark.asyncio
async def test_withdrawn_consent_is_skipped(no_history):
    _, [recipient] = await _plan([_lead(extra={"consent": "denied"})])
    assert recipient.status == MarketingRecipientStatus.skipped
    assert recipient.skip_reason == "This contact withdrew consent."


@pytest.mark.asyncio
async def test_opted_out_contact_is_skipped(no_history):
    _, [recipient] = await _plan(
        [_lead(extra={"consent": "granted", "opted_out": True})]
    )
    assert recipient.skip_reason == "This contact asked not to be contacted."


@pytest.mark.asyncio
async def test_do_not_contact_list_blocks_the_lead(monkeypatch, no_history):
    lead = _lead()
    _set_suppressed(monkeypatch, {lead.id})
    _, [recipient] = await _plan([lead])
    assert recipient.status == MarketingRecipientStatus.skipped
    assert recipient.skip_reason == "This contact is on your do-not-contact list."


@pytest.mark.asyncio
async def test_quiet_hours_skip_uses_messaging_wording(no_history):
    _, [recipient] = await _plan([_lead()], now=NIGHT)
    assert recipient.status == MarketingRecipientStatus.skipped
    assert "outside messaging hours" in recipient.skip_reason


@pytest.mark.asyncio
async def test_daily_attempt_cap_skips_the_lead(monkeypatch, no_history):
    lead = _lead()
    _set_attempts(monkeypatch, {lead.id: 2})
    _, [recipient] = await _plan([lead])
    assert recipient.status == MarketingRecipientStatus.skipped
    assert "limit" in recipient.skip_reason


@pytest.mark.asyncio
async def test_reply_window_is_never_used_when_planning(monkeypatch, no_history):
    calls: list[bool] = []
    real = svc.check_outbound

    def spy(**kwargs):
        calls.append(kwargs["is_reply"])
        return real(**kwargs)

    monkeypatch.setattr(svc, "check_outbound", spy)
    await _plan([_lead(), _lead(extra={})])
    assert calls == [False, False]


@pytest.mark.asyncio
async def test_email_lead_without_address_is_skipped_in_plain_words(no_history):
    _, [recipient] = await _plan([_lead(email=None)])
    assert recipient.status == MarketingRecipientStatus.skipped
    assert recipient.skip_reason == "This lead has no email address."


@pytest.mark.asyncio
async def test_sms_lead_needs_a_plus_country_code(no_history):
    _, [recipient] = await _plan(
        [_lead(phone="07700 900123")], channel="sms", subject=None
    )
    assert recipient.status == MarketingRecipientStatus.skipped
    assert "+ and a country code" in recipient.skip_reason


@pytest.mark.asyncio
async def test_email_campaign_needs_a_subject(no_history):
    session = ScriptedSession(scalars=[[_lead()]])
    with pytest.raises(CampaignError, match="subject"):
        await svc.create_campaign(
            session,
            organization_id=ORG,
            project_id=PROJECT,
            created_by=USER,
            name="Spring",
            channel="email",
            subject="  ",
            body="Hi",
            lead_ids=[uuid.uuid4()],
        )


@pytest.mark.asyncio
async def test_leads_outside_the_workspace_are_refused(no_history):
    session = ScriptedSession(scalars=[[]])
    with pytest.raises(CampaignError, match="not in this workspace"):
        await svc.create_campaign(
            session,
            organization_id=ORG,
            project_id=PROJECT,
            created_by=USER,
            name="Spring",
            channel="email",
            subject="Hi",
            body="Hi",
            lead_ids=[uuid.uuid4()],
        )


# ───────────────────────────── honest sending ─────────────────────────────


class _EmailMustNotBeCalled:
    async def __call__(self, *args, **kwargs):  # pragma: no cover - failure path only
        raise AssertionError("the email adapter must not be reached without a provider")


@pytest.mark.asyncio
async def test_no_email_provider_fails_honestly_through_the_real_registry(monkeypatch):
    from app.services import email_service

    monkeypatch.setattr(adapters.EmailAdapter, "send", _EmailMustNotBeCalled())
    # SMTP is not configured in tests: the email service reports "not delivered".
    monkeypatch.setattr(email_service, "send_email", lambda **_kwargs: False)
    lead = _lead()
    campaign = _campaign("email")
    recipient = _recipient(campaign, lead)

    registry_session = ScriptedSession(scalars=[[]])  # no enabled email binding
    registry = ChannelOutboundSender(
        session_factory=lambda: _SessionContext(registry_session),
        config_provider=lambda: ChannelsConfig.__new__(ChannelsConfig),
    )
    sent = await _send_one(campaign, recipient, lead, registry, monkeypatch)

    assert sent is False
    assert recipient.status == MarketingRecipientStatus.failed
    assert recipient.failure_reason == svc.PROVIDER_REFUSED_REASON
    assert recipient.sent_at is None
    assert campaign.sent_count == 0
    assert campaign.failed_count == 1


async def _send_one(campaign, recipient, lead, sender, monkeypatch):
    """Run the batch worker over one recipient. Returns True when the recipient is sent."""
    session = ScriptedSession(
        scalar=[campaign],
        execute=[[(recipient, lead)]],
    )
    monkeypatch.setattr(contact_policy_service, "suppressed_lead_ids", _none_suppressed)
    monkeypatch.setattr(svc, "attempts_last_24h", _none_attempts)
    await svc.send_next_batch(
        session,
        organization_id=ORG,
        project_id=PROJECT,
        campaign_id=campaign.id,
        sender=sender,
        unsubscribe_base_url=PUBLIC_BASE,
        now=DAYTIME,
    )
    return recipient.status == MarketingRecipientStatus.sent


async def _none_suppressed(session, *, organization_id, leads, channel):
    return set()


async def _none_attempts(session, *, organization_id, lead_ids, now):
    return {}


@pytest.mark.asyncio
async def test_sent_only_when_the_sender_returns(monkeypatch):
    lead = _lead()
    campaign = _campaign("email")
    recipient = _recipient(campaign, lead)
    spy = SpySender()

    assert await _send_one(campaign, recipient, lead, spy, monkeypatch) is True
    assert recipient.status == MarketingRecipientStatus.sent
    assert recipient.sent_at == DAYTIME
    assert campaign.sent_count == 1
    assert len(spy.calls) == 1
    assert spy.calls[0]["channel"] == "email"
    assert spy.calls[0]["recipient"] == "jane.doe@example.com"


@pytest.mark.asyncio
async def test_a_refused_message_is_marked_failed_never_sent(monkeypatch):
    lead = _lead()
    campaign = _campaign("sms")
    campaign.subject = None
    recipient = _recipient(campaign, lead)
    spy = SpySender(error=RuntimeError("provider 500 with secret detail"))

    assert await _send_one(campaign, recipient, lead, spy, monkeypatch) is False
    assert recipient.status == MarketingRecipientStatus.failed
    assert recipient.failure_reason == PROVIDER_REFUSED_REASON
    assert "secret detail" not in recipient.failure_reason


@pytest.mark.asyncio
async def test_sms_not_configured_reports_the_registry_reason(monkeypatch):
    lead = _lead()
    campaign = _campaign("sms")
    campaign.subject = None
    recipient = _recipient(campaign, lead)
    spy = SpySender(
        error=OutboundNotConfigured(
            "No enabled sms channel is set up for this organization."
        )
    )

    await _send_one(campaign, recipient, lead, spy, monkeypatch)
    assert recipient.status == MarketingRecipientStatus.failed
    assert (
        recipient.failure_reason
        == "No enabled sms channel is set up for this organization."
    )


@pytest.mark.asyncio
async def test_email_is_never_sent_without_an_unsubscribe_link(monkeypatch):
    lead = _lead()
    campaign = _campaign("email")
    recipient = _recipient(campaign, lead)
    spy = SpySender()
    session = ScriptedSession(scalar=[campaign], execute=[[(recipient, lead)]])
    monkeypatch.setattr(contact_policy_service, "suppressed_lead_ids", _none_suppressed)
    monkeypatch.setattr(svc, "attempts_last_24h", _none_attempts)

    await svc.send_next_batch(
        session,
        organization_id=ORG,
        project_id=PROJECT,
        campaign_id=campaign.id,
        sender=spy,
        unsubscribe_base_url="",
        now=DAYTIME,
    )
    assert spy.calls == []
    assert recipient.failure_reason == UNSUBSCRIBE_UNAVAILABLE_REASON


@pytest.mark.asyncio
async def test_email_body_carries_a_signed_unsubscribe_link(monkeypatch):
    lead = _lead()
    campaign = _campaign("email")
    recipient = _recipient(campaign, lead)
    spy = SpySender()
    await _send_one(campaign, recipient, lead, spy, monkeypatch)
    text = spy.calls[0]["text"]
    assert f"{PUBLIC_BASE}/api/marketing/unsubscribe?token=" in text
    token = text.split("token=", 1)[1].split()[0]
    claim = unsub.parse_unsubscribe_token(token, now=DAYTIME)
    assert claim.organization_id == ORG
    assert claim.recipient_id == recipient.id


# ───────────────────────────── double-send guard ─────────────────────────────


@pytest.mark.asyncio
async def test_begin_send_refuses_a_campaign_already_sending():
    campaign = _campaign(status=MarketingCampaignStatus.sending)
    session = ScriptedSession(scalar=[campaign])
    with pytest.raises(CampaignConflict, match="already been sent or is being sent"):
        await svc.begin_send(
            session, organization_id=ORG, project_id=PROJECT, campaign_id=campaign.id
        )
    assert len(session.statements) == 1  # only the lookup ran; no UPDATE was attempted


@pytest.mark.asyncio
async def test_begin_send_loses_the_race_when_the_claim_matches_nothing():
    campaign = _campaign(status=MarketingCampaignStatus.draft)
    session = ScriptedSession(scalar=[campaign], execute=[[]])
    with pytest.raises(CampaignConflict):
        await svc.begin_send(
            session, organization_id=ORG, project_id=PROJECT, campaign_id=campaign.id
        )


@pytest.mark.asyncio
async def test_begin_send_refuses_completed_and_cancelled_campaigns():
    for status, text in (
        (MarketingCampaignStatus.completed, "already been sent"),
        (MarketingCampaignStatus.cancelled, "was cancelled"),
    ):
        campaign = _campaign(status=status)
        session = ScriptedSession(scalar=[campaign])
        with pytest.raises(CampaignConflict, match=text):
            await svc.begin_send(
                session,
                organization_id=ORG,
                project_id=PROJECT,
                campaign_id=campaign.id,
            )


@pytest.mark.asyncio
async def test_claim_is_scoped_to_organization_and_project():
    campaign = _campaign(status=MarketingCampaignStatus.draft)
    session = ScriptedSession(scalar=[campaign], execute=[[(campaign.id,)]])
    await svc.begin_send(
        session, organization_id=ORG, project_id=PROJECT, campaign_id=campaign.id
    )
    claim_sql = _sql(session.statements[1])
    assert str(ORG) in claim_sql
    assert "status IN" in claim_sql
    assert campaign.status == MarketingCampaignStatus.sending


# ───────────────────────────── routes: roles, guard, isolation ─────────────────────────────


def _org_ctx(role="admin", org=ORG):
    return OrgContext(
        user_id=USER, auth_subject="sub", organization_id=org, membership_role=role
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


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(marketing_routes, "audit", lambda *a, **k: None)
    monkeypatch.setattr(marketing_routes, "ensure_default_senders", lambda: None)
    monkeypatch.setattr(
        marketing_routes,
        "get_channels_config",
        lambda: SimpleNamespace(public_api_base_url=PUBLIC_BASE),
    )

    async def role_only_authorize(session, ctx, *, permission=None, **_):
        if permission and not has_permission(ctx.membership_role, permission):
            raise HTTPException(
                403, f"Role '{ctx.membership_role}' lacks {permission}."
            )
        return SimpleNamespace(raise_for_denied=lambda: None)

    monkeypatch.setattr(authz, "authorize", role_only_authorize)

    state = SimpleNamespace(role="admin", session=ScriptedSession(), org=ORG)

    async def _org():
        return _org_ctx(state.role, state.org)

    async def _project():
        return _project_ctx(state.role, state.org)

    app = FastAPI()
    app.include_router(marketing_routes.router)
    app.dependency_overrides[get_current_organization] = _org
    app.dependency_overrides[get_current_project] = _project
    app.dependency_overrides[get_db] = lambda: state.session
    state.client = TestClient(app)
    return state


def _create_body():
    return {
        "name": "Spring",
        "channel": "email",
        "subject": "Hello",
        "body": "Our spring offer.",
        "lead_ids": [str(uuid.uuid4())],
    }


def test_viewer_cannot_create_send_or_cancel(api, monkeypatch):
    api.role = "viewer"
    assert (
        api.client.post("/api/marketing/campaigns", json=_create_body()).status_code
        == 403
    )
    assert (
        api.client.post(f"/api/marketing/campaigns/{uuid.uuid4()}/send").status_code
        == 403
    )
    assert (
        api.client.post(f"/api/marketing/campaigns/{uuid.uuid4()}/cancel").status_code
        == 403
    )


def test_viewer_can_read_campaigns(api, monkeypatch):
    api.role = "viewer"

    async def listing(session, *, organization_id, project_id, limit=100):
        return []

    monkeypatch.setattr(svc, "list_campaigns", listing)
    response = api.client.get("/api/marketing/campaigns")
    assert response.status_code == 200
    assert response.json() == []


def test_second_send_is_refused_and_never_reaches_the_sender(api, monkeypatch):
    sending = _campaign(status=MarketingCampaignStatus.sending)
    api.session._scalar = [
        sending,
        sending,
    ]  # get_campaign for the channel, then begin_send
    spy = SpySender()
    monkeypatch.setattr(marketing_routes, "get_outbound_sender", lambda channel: spy)

    response = api.client.post(f"/api/marketing/campaigns/{sending.id}/send")

    assert response.status_code == 409
    assert "already been sent" in response.json()["detail"]
    assert spy.calls == []


def test_send_is_refused_when_no_sender_is_registered(api, monkeypatch):
    campaign = _campaign(status=MarketingCampaignStatus.draft)
    api.session._scalar = [campaign]
    monkeypatch.setattr(marketing_routes, "get_outbound_sender", lambda channel: None)
    response = api.client.post(f"/api/marketing/campaigns/{campaign.id}/send")
    assert response.status_code == 503
    assert campaign.status == MarketingCampaignStatus.draft


def test_a_campaign_from_another_organization_is_not_found(api):
    api.session._scalar = [None]
    response = api.client.get(f"/api/marketing/campaigns/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_campaign_lookup_is_scoped_to_organization_and_project():
    session = ScriptedSession(scalar=[None])
    with pytest.raises(CampaignNotFound):
        await svc.get_campaign(
            session, organization_id=ORG, project_id=PROJECT, campaign_id=uuid.uuid4()
        )
    sql = _sql(session.statements[0])
    assert str(ORG) in sql
    assert str(PROJECT) in sql


def test_full_send_goes_through_the_sender_and_completes(api, monkeypatch):
    lead = _lead()
    campaign = _campaign("email")
    recipient = _recipient(campaign, lead)
    spy = SpySender()
    monkeypatch.setattr(marketing_routes, "get_outbound_sender", lambda channel: spy)
    monkeypatch.setattr(contact_policy_service, "suppressed_lead_ids", _none_suppressed)
    monkeypatch.setattr(svc, "attempts_last_24h", _none_attempts)
    # The route sends without an explicit clock, so the quiet-hours policy
    # (21:00-08:00 contact-local) would otherwise depend on the wall-clock time
    # the suite happens to run at. Pin the clock to a daytime instant.
    monkeypatch.setattr(svc, "_utcnow", lambda: DAYTIME)

    # get_campaign (route) | begin_send claim | batch: campaign, rows | batch end: campaign, [] | complete | detail
    api.session._scalar = [campaign] * 6
    api.session._execute = [
        [(campaign.id,)],  # claim
        [(recipient, lead)],  # first batch
        [],  # second batch: nothing left
        [],  # complete_campaign update
        [(recipient, "Jane Doe", "Jane.Doe@Example.com", "+14155550123")],  # detail
    ]

    response = api.client.post(f"/api/marketing/campaigns/{campaign.id}/send")

    assert response.status_code == 200, response.text
    assert len(spy.calls) == 1
    assert campaign.status == MarketingCampaignStatus.completed
    assert campaign.sent_count == 1
    assert response.json()["recipients"][0]["status"] == "sent"


def test_cancel_refuses_a_campaign_that_is_already_sending(api):
    campaign = _campaign(status=MarketingCampaignStatus.sending)
    api.session._scalar = [campaign]
    response = api.client.post(f"/api/marketing/campaigns/{campaign.id}/cancel")
    assert response.status_code == 409


# ───────────────────────────── unsubscribe tokens ─────────────────────────────


def test_token_round_trips_and_names_the_recipient_and_organization():
    recipient_id = uuid.uuid4()
    token = unsub.make_unsubscribe_token(
        organization_id=ORG, recipient_id=recipient_id, now=DAYTIME
    )
    claim = unsub.parse_unsubscribe_token(token, now=DAYTIME + timedelta(days=1))
    assert claim.organization_id == ORG
    assert claim.recipient_id == recipient_id


def test_token_carries_no_email_address():
    token = unsub.make_unsubscribe_token(
        organization_id=ORG, recipient_id=uuid.uuid4(), now=DAYTIME
    )
    assert "@" not in token


def test_tampered_payload_is_rejected():
    token = unsub.make_unsubscribe_token(
        organization_id=ORG, recipient_id=uuid.uuid4(), now=DAYTIME
    )
    body, signature = token.split(".", 1)
    forged = unsub._b64encode(
        b'{"e":9999999999,"o":"%s","r":"%s"}'
        % (str(OTHER_ORG).encode(), str(uuid.uuid4()).encode())
    )
    with pytest.raises(InvalidUnsubscribeToken):
        unsub.parse_unsubscribe_token(f"{forged}.{signature}", now=DAYTIME)
    assert body != forged


def test_signature_from_another_secret_is_rejected(monkeypatch):
    token = unsub.make_unsubscribe_token(
        organization_id=ORG, recipient_id=uuid.uuid4(), now=DAYTIME
    )
    monkeypatch.setattr(
        settings, "jwt_secret_key", "a-different-server-secret-0123456789abcdef"
    )
    with pytest.raises(InvalidUnsubscribeToken):
        unsub.parse_unsubscribe_token(token, now=DAYTIME)


@pytest.mark.parametrize("token", ["", "no-dot-here", "a.b.c", "x" * 2000, "%%%.%%%"])
def test_malformed_tokens_are_rejected(token):
    with pytest.raises(InvalidUnsubscribeToken):
        unsub.parse_unsubscribe_token(token, now=DAYTIME)


def test_token_is_valid_for_89_days_and_expires_at_90():
    token = unsub.make_unsubscribe_token(
        organization_id=ORG, recipient_id=uuid.uuid4(), now=DAYTIME
    )
    unsub.parse_unsubscribe_token(token, now=DAYTIME + timedelta(days=89))
    with pytest.raises(InvalidUnsubscribeToken, match="expired"):
        unsub.parse_unsubscribe_token(token, now=DAYTIME + timedelta(days=90))


@pytest.mark.asyncio
async def test_applying_a_token_adds_an_email_do_not_contact_entry(monkeypatch):
    recipient = _recipient(_campaign(), _lead())
    lead = _lead(id=recipient.lead_id, email="Jane.Doe@Example.com")
    session = ScriptedSession(scalar=[recipient, lead])
    recorded: dict = {}

    async def add_entry(session, **kwargs):
        recorded.update(kwargs)
        return SimpleNamespace(), True

    monkeypatch.setattr(contact_policy_service, "add_entry", add_entry)
    token = unsub.make_unsubscribe_token(
        organization_id=ORG, recipient_id=recipient.id, now=DAYTIME
    )

    reason = await unsub.apply_unsubscribe(session, token, now=DAYTIME)

    assert reason == "Marketing unsubscribe"
    assert recorded["organization_id"] == ORG
    assert recorded["channel_scope"] == "email"
    assert recorded["raw_value"] == "jane.doe@example.com"


@pytest.mark.asyncio
async def test_a_token_cannot_reach_another_organizations_recipient(monkeypatch):
    session = ScriptedSession(
        scalar=[None]
    )  # recipient lookup is scoped to the signed organization
    token = unsub.make_unsubscribe_token(
        organization_id=OTHER_ORG, recipient_id=uuid.uuid4(), now=DAYTIME
    )
    with pytest.raises(InvalidUnsubscribeToken):
        await unsub.apply_unsubscribe(session, token, now=DAYTIME)
    sql = _sql(session.statements[0])
    assert str(OTHER_ORG) in sql


def test_unsubscribe_page_shows_a_confirm_form_and_does_not_unsubscribe_on_get(api):
    client = TestClient(_unsub_app(api))
    response = client.get("/api/marketing/unsubscribe", params={"token": "abc"})
    assert response.status_code == 200
    assert 'method="post"' in response.text
    assert "Confirm unsubscribe" in response.text
    assert api.session.commits == 0


def test_bad_unsubscribe_token_returns_400_and_rolls_back(api):
    client = TestClient(_unsub_app(api))
    response = client.post("/api/marketing/unsubscribe", data={"token": "forged.token"})
    assert response.status_code == 400
    assert "not valid" in response.text
    assert api.session.rollbacks == 1
    assert api.session.commits == 0


def _unsub_app(api):
    app = FastAPI()
    app.include_router(marketing_routes.router)
    app.dependency_overrides[get_db] = lambda: api.session
    return app


@pytest.mark.asyncio
async def test_a_lead_deleted_after_planning_is_skipped_not_sent(
    monkeypatch, no_history
):
    lead = _lead()
    campaign = _campaign("email")
    recipient = _recipient(campaign, lead)
    lead.deleted_at = DAYTIME
    spy = SpySender()
    session = ScriptedSession(scalar=[campaign], execute=[[(recipient, lead)]])

    await svc.send_next_batch(
        session,
        organization_id=ORG,
        project_id=PROJECT,
        campaign_id=campaign.id,
        sender=spy,
        unsubscribe_base_url=PUBLIC_BASE,
        now=DAYTIME,
    )

    assert spy.calls == []
    assert recipient.status == MarketingRecipientStatus.skipped
    assert "deleted" in recipient.skip_reason


@pytest.mark.asyncio
async def test_an_unusable_email_in_an_unsubscribe_link_is_a_clean_refusal(monkeypatch):
    recipient = _recipient(_campaign(), _lead())
    lead = _lead(id=recipient.lead_id, email="not-an-address@")
    session = ScriptedSession(scalar=[recipient, lead])
    token = unsub.make_unsubscribe_token(
        organization_id=ORG, recipient_id=recipient.id, now=DAYTIME
    )
    with pytest.raises(InvalidUnsubscribeToken, match="valid email"):
        await unsub.apply_unsubscribe(session, token, now=DAYTIME)


@pytest.mark.asyncio
async def test_an_interrupted_claim_is_failed_for_review_and_never_resent(monkeypatch):
    lead = _lead()
    campaign = _campaign("email")
    recipient = _recipient(campaign, lead)
    recipient.status = MarketingRecipientStatus.sending
    recipient.claimed_at = DAYTIME - svc.SENDING_CLAIM_TIMEOUT - timedelta(minutes=1)
    spy = SpySender()
    session = ScriptedSession(scalar=[campaign], scalars=[[recipient]], execute=[[]])
    monkeypatch.setattr(contact_policy_service, "suppressed_lead_ids", _none_suppressed)
    monkeypatch.setattr(svc, "attempts_last_24h", _none_attempts)

    handled = await svc.send_next_batch(
        session,
        organization_id=ORG,
        project_id=PROJECT,
        campaign_id=campaign.id,
        sender=spy,
        unsubscribe_base_url=PUBLIC_BASE,
        now=DAYTIME,
    )

    assert handled == 0
    assert spy.calls == []
    assert recipient.status == MarketingRecipientStatus.failed
    assert "outcome is unknown" in recipient.failure_reason
    assert campaign.failed_count == 1


class _IdSender:
    """A sender that returns the provider's message id, as a real provider adapter does."""

    def __init__(self, message_id):
        self.message_id = message_id
        self.calls = []

    async def send(self, **kwargs):
        self.calls.append(kwargs)
        return self.message_id


@pytest.mark.asyncio
async def test_a_send_keeps_the_providers_message_id_and_marks_it_sent(monkeypatch):
    lead = _lead()
    campaign = _campaign("email")
    recipient = _recipient(campaign, lead)
    sender = _IdSender({"id": "msg-42"})

    assert await _send_one(campaign, recipient, lead, sender, monkeypatch) is True
    assert recipient.provider_message_id == "msg-42"
    assert recipient.delivery_status == svc.MarketingDeliveryStatus.sent


def test_provider_ids_are_read_from_string_or_dict_only():
    assert svc._as_message_id("  abc  ") == "abc"
    assert svc._as_message_id({"message_id": "m-1"}) == "m-1"
    assert svc._as_message_id(None) is None
    assert svc._as_message_id("   ") is None
    assert svc._as_message_id(12345) is None


@pytest.mark.parametrize(
    "current, incoming, expected",
    [
        (None, "delivered", True),
        ("sent", "delivered", True),
        ("delivered", "read", True),
        ("delivered", "delivered", False),
        ("read", "delivered", False),
        ("delivered", "bounced", True),
        ("bounced", "delivered", False),
        ("sent", "mystery", False),
    ],
)
def test_receipts_only_move_a_message_forward(current, incoming, expected):
    assert svc.receipt_advances(current, incoming) is expected


@pytest.mark.asyncio
async def test_receipts_are_applied_once_and_ignored_when_out_of_order(monkeypatch):
    lead = _lead()
    campaign = _campaign("email")
    recipient = _recipient(campaign, lead)
    recipient.provider_message_id = "msg-7"
    recipient.delivery_status = "sent"
    recipient.delivery_updated_at = DAYTIME
    later = DAYTIME + timedelta(minutes=5)

    async def _run(status, when):
        session = ScriptedSession(scalar=[recipient])
        return await svc.apply_delivery_receipt(
            session,
            organization_id=ORG,
            provider_message_id="msg-7",
            status=status,
            occurred_at=when,
        )

    assert await _run("delivered", later) == "applied"
    assert recipient.delivery_status == "delivered"
    assert (
        await _run("delivered", later + timedelta(minutes=1)) == "stale"
    )  # a repeat changes nothing
    assert await _run("read", later + timedelta(minutes=2)) == "applied"
    assert (
        await _run("delivered", later + timedelta(minutes=3)) == "stale"
    )  # arrives after "read"
    assert recipient.delivery_status == "read"


@pytest.mark.asyncio
async def test_a_receipt_older_than_the_last_one_applied_is_stale(monkeypatch):
    lead = _lead()
    campaign = _campaign("sms")
    recipient = _recipient(campaign, lead)
    recipient.provider_message_id = "msg-8"
    recipient.delivery_status = "delivered"
    recipient.delivery_updated_at = DAYTIME + timedelta(hours=1)
    session = ScriptedSession(scalar=[recipient])

    result = await svc.apply_delivery_receipt(
        session,
        organization_id=ORG,
        provider_message_id="msg-8",
        status="read",
        occurred_at=DAYTIME,
    )
    assert result == "stale"
    assert recipient.delivery_status == "delivered"


@pytest.mark.asyncio
async def test_receipts_for_unknown_ids_or_states_change_nothing():
    unknown = ScriptedSession(scalar=[None])
    assert (
        await svc.apply_delivery_receipt(
            unknown,
            organization_id=ORG,
            provider_message_id="nope",
            status="delivered",
            occurred_at=DAYTIME,
        )
        == "unknown"
    )

    lead = _lead()
    recipient = _recipient(_campaign("email"), lead)
    recipient.provider_message_id = "msg-9"
    recipient.delivery_status = "sent"
    odd = ScriptedSession(scalar=[recipient])
    assert (
        await svc.apply_delivery_receipt(
            odd,
            organization_id=ORG,
            provider_message_id="msg-9",
            status="teleported",
            occurred_at=DAYTIME,
        )
        == "ignored"
    )
    assert recipient.delivery_status == "sent"

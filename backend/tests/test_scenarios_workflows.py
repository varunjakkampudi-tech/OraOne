"""Workflow message scenarios: an automation sends through the organization's own channel
binding. Covers the send path, refusals when no channel is ready, provider rejection and
exceptions, and tenant-scoped binding and trigger lookups.

Channel adapters are replaced with recording fakes. No message is sent.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import httpx
import pytest

from app.database.models.workflow import WorkflowStatus
from app.services import workflow_triggers
from app.services.channels import adapters
from app.services.workflow_senders import (
    ChannelOutboundSender,
    OutboundNotConfigured,
    find_bindings,
)
from scenario_support import ORG_A, ORG_B, PROJECT_A, FakeSession, channels_config, sql

READY = dict(
    twilio_account_sid="ACscenario0000000000000000000000",
    twilio_auth_token="scenario-twilio-token",
    twilio_configured=True,
)


class _SessionContext:
    """Async context manager that yields a scripted session, as the sender expects."""

    def __init__(self, session: FakeSession) -> None:
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc) -> bool:
        return False


def _binding(org_id: uuid.UUID = ORG_A, **overrides) -> SimpleNamespace:
    base = dict(
        id=uuid.uuid4(),
        organization_id=org_id,
        agent_id=uuid.uuid4(),
        project_id=None,
        channel="sms",
        provider="twilio",
        phone_number="+15550001111",
        configuration={},
        enabled=True,
        status="active",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _sender(bindings: list, cfg) -> ChannelOutboundSender:
    session = FakeSession(scalars=[bindings])
    return ChannelOutboundSender(
        session_factory=lambda: _SessionContext(session),
        config_provider=lambda: cfg,
    )


async def _send(sender: ChannelOutboundSender, channel: str = "sms", org=ORG_A):
    return await sender.send(
        channel=channel,
        recipient="+447700900123",
        text="Your appointment is confirmed.",
        organization_id=org,
        lead_id=uuid.uuid4(),
    )


# ───────────────────────── happy path ─────────────────────────


@pytest.mark.smoke
async def test_workflow_message_goes_out_through_the_organizations_ready_binding(
    monkeypatch,
):
    binding = _binding()
    seen: dict = {}

    async def accept(self, *, binding, parsed, text):
        seen.update(binding_id=binding.id, to=parsed.reply_to, text=text)
        return True

    monkeypatch.setattr(adapters.TwilioMessagingAdapter, "send", accept)

    result = await _send(_sender([binding], channels_config(**READY)))

    assert result == {"provider": "twilio", "binding_id": str(binding.id)}
    assert seen == {
        "binding_id": binding.id,
        "to": "+447700900123",
        "text": "Your appointment is confirmed.",
    }


# ───────────────────────── refusals ─────────────────────────


@pytest.mark.critical
async def test_message_is_not_sent_when_the_organization_has_no_enabled_channel(
    monkeypatch,
):
    async def must_not_send(self, **_):
        raise AssertionError("no binding exists, so nothing may be sent")

    monkeypatch.setattr(adapters.TwilioMessagingAdapter, "send", must_not_send)

    with pytest.raises(OutboundNotConfigured, match="No enabled sms channel"):
        await _send(_sender([], channels_config(**READY)))


@pytest.mark.critical
async def test_channel_that_cannot_send_is_refused_before_any_lookup():
    session = FakeSession()
    sender = ChannelOutboundSender(
        session_factory=lambda: _SessionContext(session),
        config_provider=lambda: channels_config(**READY),
    )

    with pytest.raises(OutboundNotConfigured, match="fax channel"):
        await _send(sender, channel="fax")
    assert session.statements == []


@pytest.mark.critical
async def test_unconfigured_twilio_is_refused_without_contacting_twilio(monkeypatch):
    async def must_not_send(self, **_):
        raise AssertionError("Twilio is not configured, so it must not be called")

    monkeypatch.setattr(adapters.TwilioMessagingAdapter, "send", must_not_send)

    with pytest.raises(OutboundNotConfigured, match="Twilio is not configured"):
        await _send(_sender([_binding()], channels_config()))


# ───────────────────────── external failure ─────────────────────────


@pytest.mark.regression
async def test_provider_rejection_is_reported_as_a_failed_send(monkeypatch):
    async def rejected(self, **_):
        return False

    monkeypatch.setattr(adapters.TwilioMessagingAdapter, "send", rejected)

    with pytest.raises(RuntimeError, match="did not accept the message"):
        await _send(_sender([_binding()], channels_config(**READY)))


@pytest.mark.regression
async def test_provider_exception_is_hidden_behind_a_plain_failure(monkeypatch):
    async def explode(self, **_):
        raise httpx.ConnectError("https://api.twilio.example/with-secret-path")

    monkeypatch.setattr(adapters.TwilioMessagingAdapter, "send", explode)

    with pytest.raises(RuntimeError) as failed:
        await _send(_sender([_binding()], channels_config(**READY)))

    assert str(failed.value) == "The sms provider did not accept the message."
    assert "secret-path" not in str(failed.value)


# ───────────────────────── tenant isolation ─────────────────────────


@pytest.mark.critical
async def test_binding_lookup_is_scoped_to_the_organization_sending_the_message():
    session = FakeSession(scalars=[[]])

    bindings = await find_bindings(session, ORG_A, "whatsapp")

    assert bindings == []
    statement = sql(session.statements[0])
    assert str(ORG_A) in statement
    assert str(ORG_B) not in statement
    assert "enabled" in statement


@pytest.mark.critical
def test_workflow_triggers_only_match_active_workflows_of_the_same_org_and_project():
    stmt = workflow_triggers.matching_workflows_stmt(ORG_A, "lead.created", PROJECT_A)

    statement = sql(stmt)
    assert str(ORG_A) in statement
    assert str(ORG_B) not in statement
    assert WorkflowStatus.active in statement
    assert "deleted_at IS NULL" in statement
    assert str(PROJECT_A) in statement

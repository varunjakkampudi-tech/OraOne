"""Workflow send_message senders: channel bindings, provider readiness and consent.

No database and no network. Bindings come from in-memory AgentChannel rows, the
adapter ``send`` methods are replaced with recorders, and a guard fails any test
that tries to open a socket.
"""

from __future__ import annotations

import socket
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.database.models.agent_channel import AgentChannel, ChannelStatus
from app.database.models.lead import Lead, LeadStatus, LeadTemperature
from app.database.models.workflow import (
    RunStatus,
    RunStepStatus,
    StepType,
    Workflow,
    WorkflowRun,
    WorkflowRunStep,
    WorkflowStatus,
    WorkflowTrigger,
)
from app.services import workflow_engine as engine
from app.services import workflow_senders as senders
from app.services.channels import adapters
from app.services.channels.config import ChannelsConfig

DAYTIME = datetime(2026, 10, 17, 14, 0, tzinfo=timezone.utc)  # 15:00 in London


# ───────────────────────── guards and fixtures ─────────────────────────


_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Any connection to a non-loopback address fails the test.

    Loopback stays open because the event loop uses it for its own self-pipe.
    Adapters are also mocked, so no test should reach a provider.
    """
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def guard(real):
        def check(self, address, *args, **kwargs):
            host = address[0] if isinstance(address, tuple) else str(address)
            if host not in _LOOPBACK:
                raise AssertionError("network access is not allowed in this test")
            return real(self, address, *args, **kwargs)

        return check

    monkeypatch.setattr(socket.socket, "connect", guard(real_connect))
    monkeypatch.setattr(socket.socket, "connect_ex", guard(real_connect_ex))


@pytest.fixture(autouse=True)
def _restore_registry():
    saved = dict(engine._OUTBOUND_SENDERS)
    yield
    engine._OUTBOUND_SENDERS.clear()
    engine._OUTBOUND_SENDERS.update(saved)


@pytest.fixture
def adapter_calls(monkeypatch):
    """Replace each adapter's send with a recorder that reports success."""
    calls: list[dict] = []

    def recorder(name: str, accept: bool = True):
        async def fake_send(self, *, binding, parsed, text):
            calls.append(
                {
                    "adapter": name,
                    "provider": self.provider,
                    "binding": binding,
                    "parsed": parsed,
                    "text": text,
                }
            )
            return accept

        return fake_send

    monkeypatch.setattr(adapters.TwilioMessagingAdapter, "send", recorder("twilio"))
    monkeypatch.setattr(adapters.MetaWhatsAppAdapter, "send", recorder("meta_whatsapp"))
    monkeypatch.setattr(
        adapters.MetaInstagramAdapter, "send", recorder("meta_instagram")
    )
    monkeypatch.setattr(adapters.EmailAdapter, "send", recorder("email", accept=False))
    return calls


def _config(**overrides) -> ChannelsConfig:
    cfg = ChannelsConfig.__new__(ChannelsConfig)
    values = dict(
        twilio_account_sid="AC_test",
        twilio_auth_token="token_test",
        twilio_phone_number="+15550000000",
        meta_whatsapp_access_token="meta_wa_test",
        meta_whatsapp_app_secret="",
        meta_whatsapp_verify_token="",
        meta_instagram_access_token="meta_ig_test",
        public_api_base_url="",
        voice_handoff_number="",
        voice_say_voice="alice",
    )
    values.update(overrides)
    for key, value in values.items():
        setattr(cfg, key, value)
    return cfg


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class FakeBindingSession:
    """Async session stand-in: returns the given bindings and records statements."""

    def __init__(self, bindings=()):
        self.bindings = list(bindings)
        self.statements: list = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def scalars(self, stmt):
        self.statements.append(stmt)
        return _Result(self.bindings)


def _binding(
    org_id: uuid.UUID, channel: str, provider: str, **overrides
) -> AgentChannel:
    values = dict(
        id=uuid.uuid4(),
        organization_id=org_id,
        agent_id=uuid.uuid4(),
        channel=channel,
        provider=provider,
        enabled=True,
        status=ChannelStatus.active,
        phone_number=None,
        configuration={},
    )
    values.update(overrides)
    return AgentChannel(**values)


def _sender(bindings, cfg: ChannelsConfig | None = None):
    session = FakeBindingSession(bindings)
    sender = senders.ChannelOutboundSender(
        session_factory=lambda: session,
        config_provider=lambda: cfg or _config(),
    )
    return sender, session


def _sql(stmt) -> str:
    return str(
        stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


# ───────────────────────── binding lookup ─────────────────────────


async def test_binding_lookup_is_scoped_to_org_channel_and_enabled_bindings():
    org = uuid.uuid4()
    session = FakeBindingSession([])

    await senders.find_bindings(session, org, "whatsapp")

    sql = _sql(session.statements[0])
    assert str(org) in sql
    assert "'whatsapp'" in sql
    assert "enabled IS true" in sql or "enabled = true" in sql
    assert "status" in sql


# ───────────────────────── channel dispatch ─────────────────────────


async def test_whatsapp_via_twilio_binding_uses_the_twilio_adapter(adapter_calls):
    org = uuid.uuid4()
    binding = _binding(org, "whatsapp", "twilio", phone_number="+15550001111")
    sender, _ = _sender([binding])

    details = await sender.send(
        channel="whatsapp",
        recipient="+447700900123",
        text="Hello",
        organization_id=org,
        lead_id=uuid.uuid4(),
    )

    assert len(adapter_calls) == 1
    call = adapter_calls[0]
    assert call["adapter"] == "twilio"
    assert call["parsed"].reply_to == "whatsapp:+447700900123"
    assert call["parsed"].to_address == "+15550001111"
    assert call["text"] == "Hello"
    assert details == {"provider": "twilio", "binding_id": str(binding.id)}


async def test_whatsapp_via_meta_binding_uses_the_cloud_api_adapter(adapter_calls):
    org = uuid.uuid4()
    binding = _binding(
        org, "whatsapp", "meta", configuration={"phone_number_id": "1234567890"}
    )
    sender, _ = _sender([binding])

    await sender.send(
        channel="whatsapp",
        recipient="+44 7700 900123",
        text="Hi",
        organization_id=org,
        lead_id=uuid.uuid4(),
    )

    assert [c["adapter"] for c in adapter_calls] == ["meta_whatsapp"]
    assert adapter_calls[0]["parsed"].reply_to == "447700900123"  # digits, no '+'
    assert adapter_calls[0]["parsed"].to_address == "1234567890"


async def test_sms_uses_the_twilio_adapter_without_a_whatsapp_prefix(adapter_calls):
    org = uuid.uuid4()
    sender, _ = _sender([_binding(org, "sms", "twilio", phone_number="+15550001111")])

    await sender.send(
        channel="sms",
        recipient="+447700900123",
        text="Hi",
        organization_id=org,
        lead_id=uuid.uuid4(),
    )

    assert [c["adapter"] for c in adapter_calls] == ["twilio"]
    assert adapter_calls[0]["parsed"].reply_to == "+447700900123"


async def test_instagram_uses_the_meta_instagram_adapter(adapter_calls):
    org = uuid.uuid4()
    binding = _binding(
        org,
        "instagram",
        "meta_instagram",
        configuration={"instagram_account_id": "17841"},
    )
    sender, _ = _sender([binding])

    await sender.send(
        channel="instagram",
        recipient="igsid-998",
        text="Hi",
        organization_id=org,
        lead_id=uuid.uuid4(),
    )

    assert [c["adapter"] for c in adapter_calls] == ["meta_instagram"]
    assert adapter_calls[0]["parsed"].reply_to == "igsid-998"
    assert adapter_calls[0]["parsed"].to_address == "17841"


async def test_email_is_sent_through_the_email_service_not_the_inbound_adapter(
    monkeypatch, adapter_calls
):
    from app.services import email_service

    sent: list[dict] = []

    def fake_send_email(**kwargs):
        sent.append(kwargs)
        return True

    monkeypatch.setattr(email_service, "send_email", fake_send_email)
    org = uuid.uuid4()
    sender, _ = _sender([_binding(org, "email", "email")])

    details = await sender.send(
        channel="email",
        recipient="ada@example.com",
        text="Hi",
        organization_id=org,
        lead_id=uuid.uuid4(),
    )

    assert adapter_calls == []
    assert [m["to"] for m in sent] == ["ada@example.com"]
    assert details == {"provider": "email", "binding_id": None}


async def test_adapter_refusal_is_a_failure_with_no_provider_detail(
    monkeypatch, adapter_calls
):
    async def refused(self, *, binding, parsed, text):
        return False

    monkeypatch.setattr(adapters.TwilioMessagingAdapter, "send", refused)
    org = uuid.uuid4()
    sender, _ = _sender([_binding(org, "sms", "twilio", phone_number="+15550001111")])

    with pytest.raises(RuntimeError, match="did not accept the message") as info:
        await sender.send(
            channel="sms",
            recipient="+447700900123",
            text="Hi",
            organization_id=org,
            lead_id=uuid.uuid4(),
        )
    assert "token" not in str(info.value).lower()


# ───────────────────────── missing binding and configuration ─────────────────────────


async def test_missing_binding_fails_with_a_reason_and_sends_nothing(adapter_calls):
    org = uuid.uuid4()
    sender, session = _sender([])

    with pytest.raises(
        senders.OutboundNotConfigured, match="No enabled sms channel is set up"
    ):
        await sender.send(
            channel="sms",
            recipient="+447700900123",
            text="Hi",
            organization_id=org,
            lead_id=uuid.uuid4(),
        )
    assert adapter_calls == []
    assert len(session.statements) == 1


async def test_binding_from_another_org_is_not_used(adapter_calls):
    """The lookup is org-scoped in SQL; an empty result therefore means no send."""
    org, other = uuid.uuid4(), uuid.uuid4()
    session = FakeBindingSession([])
    sender = senders.ChannelOutboundSender(
        session_factory=lambda: session, config_provider=lambda: _config()
    )
    with pytest.raises(senders.OutboundNotConfigured):
        await sender.send(
            channel="sms",
            recipient="+447700900123",
            text="Hi",
            organization_id=org,
            lead_id=uuid.uuid4(),
        )
    assert str(org) in _sql(session.statements[0])
    assert str(other) not in _sql(session.statements[0])
    assert adapter_calls == []


async def test_missing_twilio_token_fails_with_a_reason(adapter_calls):
    org = uuid.uuid4()
    cfg = _config(twilio_auth_token="")
    sender, _ = _sender(
        [_binding(org, "sms", "twilio", phone_number="+15550001111")], cfg
    )

    with pytest.raises(senders.OutboundNotConfigured, match="Twilio is not configured"):
        await sender.send(
            channel="sms",
            recipient="+447700900123",
            text="Hi",
            organization_id=org,
            lead_id=uuid.uuid4(),
        )
    assert adapter_calls == []


async def test_missing_instagram_token_fails_with_a_reason(adapter_calls):
    org = uuid.uuid4()
    cfg = _config(meta_instagram_access_token="")
    sender, _ = _sender(
        [
            _binding(
                org,
                "instagram",
                "meta_instagram",
                configuration={"instagram_account_id": "1"},
            )
        ],
        cfg,
    )

    with pytest.raises(senders.OutboundNotConfigured, match="Instagram access token"):
        await sender.send(
            channel="instagram",
            recipient="igsid",
            text="Hi",
            organization_id=org,
            lead_id=uuid.uuid4(),
        )
    assert adapter_calls == []


async def test_disabled_binding_is_not_a_send_target(adapter_calls):
    """Disabled bindings are filtered in SQL, so a disabled-only org gets no send."""
    org = uuid.uuid4()
    session = FakeBindingSession([])  # the SQL filter would return nothing for it
    sender = senders.ChannelOutboundSender(
        session_factory=lambda: session, config_provider=lambda: _config()
    )
    with pytest.raises(senders.OutboundNotConfigured):
        await sender.send(
            channel="whatsapp",
            recipient="+447700900123",
            text="Hi",
            organization_id=org,
            lead_id=uuid.uuid4(),
        )
    assert "enabled" in _sql(session.statements[0])
    assert adapter_calls == []


# ───────────────────────── engine integration ─────────────────────────


class FakeSession:
    def __init__(self) -> None:
        self.added: list = []
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None and hasattr(obj, "__table__"):
                obj.id = uuid.uuid4()

    def add(self, obj) -> None:
        self.added.append(obj)

    async def execute(self, stmt):
        return SimpleNamespace(rowcount=1)

    async def scalar(self, stmt):
        return None

    @asynccontextmanager
    async def begin_nested(self):
        yield self


def _lead(org_id: uuid.UUID, **overrides) -> Lead:
    values = dict(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=None,
        conversation_id=None,
        name="Ada Lovelace",
        email="ada@example.com",
        phone="+447700900123",
        company=None,
        intent=None,
        source="widget",
        status=LeadStatus.new,
        temperature=LeadTemperature.hot,
        score=80,
        extra={"consent": "granted", "timezone": "Europe/London"},
    )
    values.update(overrides)
    return Lead(**values)


def _workflow(org_id: uuid.UUID) -> Workflow:
    return Workflow(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Follow up",
        status=WorkflowStatus.active,
        trigger_type=WorkflowTrigger.event,
        trigger_config={"event": "lead.created"},
        run_count=0,
        success_count=0,
        created_by=None,
    )


def _run_with_send_step(workflow: Workflow, config: dict):
    run = WorkflowRun(
        id=uuid.uuid4(),
        workflow_id=workflow.id,
        organization_id=workflow.organization_id,
        status=RunStatus.running,
        trigger=WorkflowTrigger.event,
        input={},
        output={},
        steps_total=1,
        steps_completed=0,
    )
    step = WorkflowRunStep(
        id=uuid.uuid4(),
        run_id=run.id,
        organization_id=workflow.organization_id,
        order_index=0,
        type=StepType.notification,
        name="send",
        status=RunStepStatus.pending,
        config={"action": "send_message", **config},
        input={},
        output={},
    )
    return run, [step]


@pytest.fixture
def engine_clock(monkeypatch):
    monkeypatch.setattr(engine, "_utcnow", lambda: DAYTIME)
    monkeypatch.setattr(engine, "_audit_run", lambda *a, **k: None)

    async def no_history(*_args, **_kwargs):
        return 0

    async def no_inbound(*_args, **_kwargs):
        return None

    monkeypatch.setattr(engine, "_attempts_last_24h", no_history)
    monkeypatch.setattr(engine, "_last_inbound_at", no_inbound)


async def _run_send_step(monkeypatch, lead: Lead, config: dict):
    async def load_lead(_session, _workflow, _context):
        return lead

    monkeypatch.setattr(engine, "_load_lead", load_lead)
    workflow = _workflow(lead.organization_id)
    run, steps = _run_with_send_step(workflow, config)
    await engine._run_loop(FakeSession(), workflow, run, steps, {}, start_index=0)
    return run, steps[0]


async def test_engine_records_provider_and_binding_on_the_run_step(
    monkeypatch, adapter_calls, engine_clock
):
    org = uuid.uuid4()
    binding = _binding(org, "sms", "twilio", phone_number="+15550001111")
    sender, _ = _sender([binding])
    engine.register_outbound_sender("sms", sender)

    run, step = await _run_send_step(
        monkeypatch, _lead(org), {"channel": "sms", "message": "Hi"}
    )

    assert step.status == RunStepStatus.completed
    assert step.output["sent"] is True
    assert step.output["dispatched"] is True
    assert step.output["provider"] == "twilio"
    assert step.output["binding_id"] == str(binding.id)
    assert run.status == RunStatus.completed
    assert len(adapter_calls) == 1


async def test_engine_fails_the_step_with_a_reason_when_no_binding_exists(
    monkeypatch, adapter_calls, engine_clock
):
    org = uuid.uuid4()
    sender, _ = _sender([])
    engine.register_outbound_sender("sms", sender)

    run, step = await _run_send_step(
        monkeypatch, _lead(org), {"channel": "sms", "message": "Hi"}
    )

    assert step.status == RunStepStatus.failed
    assert "No enabled sms channel is set up" in step.error_message
    assert step.output["dispatched"] is False
    assert step.output.get("sent") is None
    assert run.status == RunStatus.failed
    assert adapter_calls == []


async def test_consent_refusal_stops_before_any_lookup_or_send(
    monkeypatch, adapter_calls, engine_clock
):
    org = uuid.uuid4()
    session = FakeBindingSession(
        [_binding(org, "sms", "twilio", phone_number="+15550001111")]
    )
    sender = senders.ChannelOutboundSender(
        session_factory=lambda: session, config_provider=lambda: _config()
    )
    engine.register_outbound_sender("sms", sender)
    lead = _lead(org, extra={"consent": "unknown", "timezone": "Europe/London"})

    run, step = await _run_send_step(
        monkeypatch, lead, {"channel": "sms", "message": "Hi"}
    )

    assert step.status == RunStepStatus.skipped
    assert "consent" in step.output["reason"].lower()
    assert step.output["dispatched"] is False
    assert session.statements == []
    assert adapter_calls == []
    assert run.status == RunStatus.completed


async def test_instagram_lead_is_addressed_by_its_instagram_id(
    monkeypatch, adapter_calls, engine_clock
):
    org = uuid.uuid4()
    sender, _ = _sender(
        [
            _binding(
                org,
                "instagram",
                "meta_instagram",
                configuration={"instagram_account_id": "1"},
            )
        ]
    )
    engine.register_outbound_sender("instagram", sender)
    lead = _lead(org, extra={"consent": "granted", "instagram_id": "igsid-42"})

    _run, step = await _run_send_step(
        monkeypatch, lead, {"channel": "instagram", "message": "Hi"}
    )

    assert step.status == RunStepStatus.completed
    assert adapter_calls[0]["parsed"].reply_to == "igsid-42"


def test_ensure_default_senders_keeps_an_explicit_registration():
    explicit = object()
    engine.register_outbound_sender("sms", explicit)  # type: ignore[arg-type]

    engine.ensure_default_senders()

    assert engine.get_outbound_sender("sms") is explicit
    assert isinstance(
        engine.get_outbound_sender("whatsapp"), senders.ChannelOutboundSender
    )
    assert isinstance(
        engine.get_outbound_sender("instagram"), senders.ChannelOutboundSender
    )
    assert isinstance(
        engine.get_outbound_sender("email"), senders.ChannelOutboundSender
    )

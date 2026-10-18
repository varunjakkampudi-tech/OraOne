"""Workflow send_message email: the sender calls the email service.

No database, no SMTP. ``email_service.send_email`` is replaced with a recorder,
and a guard fails any test that opens a non-loopback socket.
"""

from __future__ import annotations

import socket
import uuid

import pytest

from app.services import email_service
from app.services import workflow_senders as senders

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
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


class _NoBindingSession:
    """Email does not read AgentChannel bindings. Any lookup is a test failure."""

    def __init__(self) -> None:
        self.opened = 0

    def __call__(self):
        self.opened += 1
        raise AssertionError("email sends must not look up channel bindings")


class _EmailRecorder:
    """Records send_email calls. Reports delivery (True) unless refused."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.delivered = True

    def __len__(self) -> int:
        return len(self.calls)

    def __getitem__(self, index: int) -> dict:
        return self.calls[index]

    def __iter__(self):
        return iter(self.calls)

    def __eq__(self, other) -> bool:
        return self.calls == other

    def refuse(self) -> None:
        self.delivered = False


@pytest.fixture
def sent(monkeypatch):
    recorder = _EmailRecorder()

    def fake_send_email(**kwargs):
        recorder.calls.append(kwargs)
        return recorder.delivered

    monkeypatch.setattr(email_service, "send_email", fake_send_email)
    return recorder


def _sender(session_factory=None):
    return senders.ChannelOutboundSender(
        session_factory=session_factory or _NoBindingSession(),
        config_provider=lambda: None,  # email never reads channel config
    )


async def test_successful_send_sends_exactly_one_email_to_the_recipient(sent):
    org = uuid.uuid4()
    session = _NoBindingSession()

    details = await _sender(session).send(
        channel="email",
        recipient="  Ada@Example.COM ",
        text="Your demo is booked.\nSee you Monday.",
        organization_id=org,
        lead_id=uuid.uuid4(),
        subject="Demo booked",
    )

    assert details == {"provider": "email", "binding_id": None}
    assert len(sent) == 1
    call = sent[0]
    assert call["to"] == "ada@example.com"
    assert call["subject"] == "Demo booked"
    assert call["template"] == senders.EMAIL_TEMPLATE
    assert call["context"] == {"message": "Your demo is booked.\nSee you Monday."}
    assert session.opened == 0


async def test_missing_subject_uses_the_default_subject(sent):
    await _sender().send(
        channel="email",
        recipient="ada@example.com",
        text="Hi",
        organization_id=uuid.uuid4(),
        lead_id=uuid.uuid4(),
    )

    assert sent[0]["subject"] == senders.DEFAULT_EMAIL_SUBJECT


async def test_failed_send_reports_failure_not_success(sent):
    sent.refuse()  # send_email returns False: SMTP missing or refused

    with pytest.raises(RuntimeError, match="did not accept the message") as info:
        await _sender().send(
            channel="email",
            recipient="ada@example.com",
            text="Hi",
            organization_id=uuid.uuid4(),
            lead_id=uuid.uuid4(),
        )

    assert len(sent) == 1
    # A refused send may have reached the provider, so it is a plain failure and
    # not OutboundNotConfigured (which the engine treats as safe to retry).
    assert not isinstance(info.value, senders.OutboundNotConfigured)
    assert "ada@example.com" not in str(info.value)


@pytest.mark.parametrize(
    "recipient",
    ["", "   ", "not-an-email", "ada@", "@example.com", "ada smith@example.com"],
)
async def test_malformed_or_missing_recipient_fails_validation_without_sending(
    sent, recipient
):
    session = _NoBindingSession()

    with pytest.raises(senders.OutboundNotConfigured, match="not valid"):
        await _sender(session).send(
            channel="email",
            recipient=recipient,
            text="Hi",
            organization_id=uuid.uuid4(),
            lead_id=uuid.uuid4(),
        )

    assert sent == []
    assert session.opened == 0


def test_normalise_email_address_matches_auth_trimming_and_lowercasing():
    assert senders.normalise_email_address("  Ada@Example.com ") == "ada@example.com"
    assert senders.normalise_email_address("a@b.co") == "a@b.co"
    assert senders.normalise_email_address("a@b") is None
    assert senders.normalise_email_address(None) is None
    assert senders.normalise_email_address("x" * 250 + "@a.co") is None


def test_email_template_renders_the_message_escaped():
    html = email_service.render(
        senders.EMAIL_TEMPLATE,
        "Hello",
        {"message": "<script>alert(1)</script>"},
    )

    assert "&lt;script&gt;" in html
    assert "<script>alert(1)</script>" not in html

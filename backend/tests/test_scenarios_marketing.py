"""Marketing campaign scenarios: the consent and suppression policy, the signed unsubscribe
link, send failures recorded per recipient, and tenant-bound unsubscribe tokens.

Senders are recording fakes, the clock is pinned, and the signing key is a fixed test value.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.marketing import campaigns
from app.services.marketing import unsubscribe
from app.services.workflow_senders import OutboundNotConfigured
from scenario_support import ORG_A, ORG_B, FakeSession, QUIET_HOURS, DAYTIME, sql

TEST_SIGNING_SECRET = "scenario-marketing-signing-secret-0123456789"
BASE_URL = "https://api.example.test"
ISSUED = datetime(2026, 10, 19, 9, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def fixed_signing_key(monkeypatch):
    monkeypatch.setattr(unsubscribe.settings, "jwt_secret_key", TEST_SIGNING_SECRET)


class RecordingSender:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.sent: list[dict] = []

    async def send(self, *, channel, recipient, text, organization_id, lead_id):
        self.sent.append(
            {
                "channel": channel,
                "recipient": recipient,
                "text": text,
                "organization_id": organization_id,
            }
        )
        if self.error is not None:
            raise self.error
        return {"accepted": True}


def _email_campaign(org_id: uuid.UUID = ORG_A):
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=org_id,
        channel="email",
        body="Our spring offer starts Monday.",
    )


def _recipient():
    return SimpleNamespace(id=uuid.uuid4())


def _lead(extra: dict | None = None, email: str = "ada@example.test"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        email=email,
        phone=None,
        extra={"consent": "granted"} if extra is None else extra,
        deleted_at=None,
    )


async def _deliver(campaign, sender, *, base_url=BASE_URL, recipient=None, lead=None):
    return await campaigns._deliver(
        campaign,
        recipient=recipient or _recipient(),
        lead=lead or _lead(),
        address="ada@example.test",
        sender=sender,
        unsubscribe_base_url=base_url,
        now=ISSUED,
    )


# ───────────────────────── happy path ─────────────────────────


@pytest.mark.smoke
async def test_email_campaign_carries_a_working_unsubscribe_link_for_its_recipient():
    campaign = _email_campaign()
    recipient = _recipient()
    sender = RecordingSender()

    failure = await _deliver(campaign, sender, recipient=recipient)

    assert failure is None
    assert len(sender.sent) == 1
    sent = sender.sent[0]
    assert sent["organization_id"] == ORG_A
    assert sent["recipient"] == "ada@example.test"
    link = sent["text"].split("unsubscribe: ", 1)[1].strip()
    assert link.startswith(f"{BASE_URL}/api/marketing/unsubscribe?token=")
    claim = unsubscribe.parse_unsubscribe_token(link.split("token=", 1)[1], now=ISSUED)
    assert claim.organization_id == ORG_A
    assert claim.recipient_id == recipient.id


# ───────────────────────── refusals ─────────────────────────


@pytest.mark.critical
@pytest.mark.parametrize(
    ("lead", "now", "fragment"),
    [
        (_lead(extra={"consent": "unknown"}), DAYTIME, "consent"),
        (_lead(extra={"consent": "denied"}), DAYTIME, "consent"),
        (_lead(extra={"consent": "granted", "opted_out": True}), DAYTIME, "asked not"),
        (_lead(extra={"consent": "granted"}), QUIET_HOURS, "outside messaging hours"),
    ],
    ids=["no-consent", "consent-denied", "opted-out", "quiet-hours"],
)
def test_policy_refuses_a_recipient_without_consent_after_opt_out_or_in_quiet_hours(
    lead, now, fragment
):
    reasons = campaigns.policy_reasons(
        lead=lead,
        channel="email",
        suppressed=False,
        attempts_last_24h=0,
        now=now,
        org_timezone="UTC",
    )

    assert reasons
    assert any(fragment in reason for reason in reasons)


@pytest.mark.critical
def test_suppressed_address_is_refused_even_with_consent():
    reasons = campaigns.policy_reasons(
        lead=_lead(),
        channel="email",
        suppressed=True,
        attempts_last_24h=0,
        now=DAYTIME,
        org_timezone="UTC",
    )

    assert reasons


@pytest.mark.critical
def test_unsubscribe_token_with_a_tampered_claim_is_refused():
    token = unsubscribe.make_unsubscribe_token(
        organization_id=ORG_A, recipient_id=uuid.uuid4(), now=ISSUED
    )
    body, signature = token.split(".", 1)
    payload = json.loads(
        base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)).decode()
    )
    payload["o"] = str(ORG_B)
    forged_body = (
        base64.urlsafe_b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        )
        .rstrip(b"=")
        .decode()
    )
    forged = f"{forged_body}.{signature}"

    with pytest.raises(unsubscribe.InvalidUnsubscribeToken):
        unsubscribe.parse_unsubscribe_token(forged, now=ISSUED)


@pytest.mark.critical
def test_expired_unsubscribe_link_is_refused_with_a_plain_reason():
    token = unsubscribe.make_unsubscribe_token(
        organization_id=ORG_A,
        recipient_id=uuid.uuid4(),
        now=ISSUED - unsubscribe.TOKEN_TTL - timedelta(days=1),
    )

    with pytest.raises(unsubscribe.InvalidUnsubscribeToken, match="expired"):
        unsubscribe.parse_unsubscribe_token(token, now=ISSUED)


# ───────────────────────── external failure ─────────────────────────


@pytest.mark.regression
async def test_provider_exception_is_recorded_as_a_refused_send_without_its_detail():
    sender = RecordingSender(error=RuntimeError("smtp password leaked here"))

    failure = await _deliver(_email_campaign(), sender)

    assert failure == campaigns.PROVIDER_REFUSED_REASON
    assert "smtp" not in failure


@pytest.mark.regression
async def test_email_without_a_connected_provider_is_recorded_as_not_sent():
    sender = RecordingSender(error=OutboundNotConfigured("no provider"))

    failure = await _deliver(_email_campaign(), sender)

    assert failure == campaigns.EMAIL_NO_PROVIDER_REASON


@pytest.mark.regression
async def test_email_is_not_sent_when_no_unsubscribe_origin_is_configured():
    sender = RecordingSender()

    failure = await _deliver(_email_campaign(), sender, base_url="")

    assert failure == campaigns.UNSUBSCRIBE_UNAVAILABLE_REASON
    assert sender.sent == []


# ───────────────────────── tenant isolation ─────────────────────────


@pytest.mark.critical
async def test_unsubscribe_for_a_recipient_of_another_tenant_changes_nothing():
    recipient_of_b = uuid.uuid4()
    token = unsubscribe.make_unsubscribe_token(
        organization_id=ORG_A, recipient_id=recipient_of_b, now=ISSUED
    )
    session = FakeSession()

    with pytest.raises(unsubscribe.InvalidUnsubscribeToken):
        await unsubscribe.apply_unsubscribe(session, token, now=ISSUED)

    assert session.added == []
    assert session.commits == 0
    statement = sql(session.statements[0])
    assert str(ORG_A) in statement
    assert str(ORG_B) not in statement
    assert str(recipient_of_b) in statement

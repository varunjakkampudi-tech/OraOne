"""Outbound contact policy at the edges users rely on: boundaries, channels and combined refusals.

Complements test_outreach_policy.py. Pure logic: no database, no network.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

import pytest

from app.services.outreach_policy import ContactState, check_outbound, in_quiet_hours

DAY = datetime(
    2026, 10, 17, 12, 0, tzinfo=timezone.utc
)  # noon UTC, outside quiet hours everywhere


def _state(**overrides) -> ContactState:
    base = dict(
        consent="given", timezone=None, last_inbound_at=None, attempts_last_24h=0
    )
    base.update(overrides)
    return ContactState(**base)


def test_suppression_beats_a_recent_reply():
    contact = _state(suppressed=True, last_inbound_at=DAY - timedelta(minutes=5))
    decision = check_outbound(contact=contact, channel="whatsapp", now=DAY)
    assert decision.allowed is False
    assert "do-not-contact" in decision.reasons[0]


def test_reply_exactly_24_hours_after_the_customer_wrote_is_still_allowed():
    contact = _state(consent="unknown", last_inbound_at=DAY - timedelta(hours=24))
    assert (
        check_outbound(
            contact=contact, channel="whatsapp", now=DAY, is_reply=True
        ).allowed
        is True
    )


def test_reply_one_second_after_the_window_needs_consent():
    contact = _state(
        consent="unknown", last_inbound_at=DAY - timedelta(hours=24, seconds=1)
    )
    decision = check_outbound(contact=contact, channel="whatsapp", now=DAY)
    assert decision.allowed is False
    assert "consent" in decision.reasons[0]


def test_an_inbound_timestamp_in_the_future_does_not_open_a_reply_window():
    contact = _state(consent="unknown", last_inbound_at=DAY + timedelta(minutes=10))
    assert check_outbound(contact=contact, channel="sms", now=DAY).allowed is False


@pytest.mark.parametrize(
    "hour, minute, quiet",
    [
        (7, 59, True),
        (8, 0, False),
        (20, 59, False),
        (21, 0, True),
        (23, 30, True),
        (2, 0, True),
    ],
)
def test_quiet_hours_boundaries_are_08_to_21_local(hour, minute, quiet):
    assert in_quiet_hours(time(hour, minute)) is quiet


def test_proactive_sms_at_night_is_blocked_just_like_a_call():
    night = datetime(2026, 10, 17, 23, 30, tzinfo=timezone.utc)
    decision = check_outbound(
        contact=_state(), channel="sms", now=night, org_timezone="UTC"
    )
    assert decision.allowed is False
    assert "outside calling hours" in decision.reasons[0]


def test_an_inbound_message_at_night_waives_consent_but_not_quiet_hours():
    # Changed: the reply window used to skip quiet hours entirely. Now a reply at night is refused.
    night = datetime(2026, 10, 17, 23, 30, tzinfo=timezone.utc)
    contact = _state(consent="unknown", last_inbound_at=night - timedelta(minutes=3))
    decision = check_outbound(
        contact=contact,
        channel="whatsapp",
        now=night,
        org_timezone="UTC",
        is_reply=True,
    )
    assert decision.allowed is False
    assert decision.reasons == [
        "It is outside calling hours for this contact (08:00 to 21:00 local)."
    ]


def test_attempt_cap_allows_the_last_attempt_and_blocks_the_next():
    assert (
        check_outbound(
            contact=_state(attempts_last_24h=1), channel="call", now=DAY
        ).allowed
        is True
    )
    blocked = check_outbound(
        contact=_state(attempts_last_24h=2), channel="call", now=DAY
    )
    assert blocked.allowed is False
    assert "limit of 2 attempts" in blocked.reasons[0]


def test_custom_attempt_cap_is_honoured():
    decision = check_outbound(
        contact=_state(attempts_last_24h=3),
        channel="call",
        now=DAY,
        max_attempts_per_day=3,
    )
    assert decision.allowed is False


def test_every_failing_rule_is_reported_so_staff_see_the_full_picture():
    night = datetime(2026, 10, 17, 23, 30, tzinfo=timezone.utc)
    contact = _state(consent="unknown", attempts_last_24h=5)
    decision = check_outbound(
        contact=contact, channel="call", now=night, org_timezone="UTC"
    )
    assert decision.allowed is False
    assert len(decision.reasons) == 3
    assert any("consent" in r for r in decision.reasons)
    assert any("calling hours" in r for r in decision.reasons)
    assert any("limit" in r for r in decision.reasons)


def test_a_contact_with_consent_in_their_own_daytime_is_reachable_across_timezones():
    # 14:00 in Tokyo is 05:00 UTC: quiet for the organization in UTC, fine for the contact.
    early_utc = datetime(2026, 10, 17, 5, 0, tzinfo=timezone.utc)
    contact = _state(timezone="Asia/Tokyo")
    assert (
        check_outbound(
            contact=contact, channel="call", now=early_utc, org_timezone="UTC"
        ).allowed
        is True
    )

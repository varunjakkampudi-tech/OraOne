"""Outbound contact policy: consent, suppression, quiet hours, reply window and attempt cap."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.outreach_policy import ContactState, check_outbound, in_quiet_hours

# 14:00 UTC is 15:00 in London and 10:00 in New York: inside calling hours for both.
DAYTIME = datetime(2026, 10, 17, 14, 0, tzinfo=timezone.utc)
# 23:30 UTC is 00:30 in London the next day: inside quiet hours.
NIGHT = datetime(2026, 10, 17, 23, 30, tzinfo=timezone.utc)


def _given(**overrides) -> ContactState:
    base = {"consent": "given", "timezone": "Europe/London"}
    base.update(overrides)
    return ContactState(**base)


def test_suppressed_contact_is_never_contacted_even_with_consent():
    decision = check_outbound(
        contact=_given(suppressed=True), channel="call", now=DAYTIME
    )
    assert decision.allowed is False
    assert any("do-not-contact" in r for r in decision.reasons)


def test_opted_out_contact_is_never_contacted_even_during_reply_window():
    state = _given(opted_out=True, last_inbound_at=DAYTIME - timedelta(hours=1))
    decision = check_outbound(contact=state, channel="whatsapp", now=DAYTIME)
    assert decision.allowed is False


def test_withdrawn_consent_blocks_contact_even_during_reply_window():
    state = _given(consent="withdrawn", last_inbound_at=DAYTIME - timedelta(hours=1))
    assert (
        check_outbound(contact=state, channel="whatsapp", now=DAYTIME).allowed is False
    )


def test_reply_within_24_hours_is_allowed_without_recorded_consent():
    state = ContactState(
        consent="unknown", last_inbound_at=DAYTIME - timedelta(hours=3)
    )
    assert (
        check_outbound(
            contact=state, channel="whatsapp", now=DAYTIME, is_reply=True
        ).allowed
        is True
    )


def test_proactive_message_inside_24_hours_still_needs_consent():
    state = ContactState(
        consent="unknown", last_inbound_at=DAYTIME - timedelta(hours=3)
    )
    decision = check_outbound(contact=state, channel="whatsapp", now=DAYTIME)
    assert decision.allowed is False
    assert any("consent" in r for r in decision.reasons)


def test_reply_window_closes_after_24_hours():
    state = ContactState(
        consent="unknown", last_inbound_at=DAYTIME - timedelta(hours=25)
    )
    decision = check_outbound(contact=state, channel="whatsapp", now=DAYTIME)
    assert decision.allowed is False


def test_proactive_outbound_without_consent_is_blocked():
    state = ContactState(consent="unknown", timezone="Europe/London")
    decision = check_outbound(contact=state, channel="call", now=DAYTIME)
    assert decision.allowed is False
    assert any("consent" in r for r in decision.reasons)


def test_outbound_with_consent_during_day_is_allowed():
    decision = check_outbound(contact=_given(), channel="call", now=DAYTIME)
    assert decision.allowed is True
    assert decision.reasons == []


def test_quiet_hours_block_outbound_in_contact_local_time():
    decision = check_outbound(contact=_given(), channel="call", now=NIGHT)
    assert decision.allowed is False
    assert any("calling hours" in r for r in decision.reasons)


def test_quiet_hours_use_contact_timezone_not_organization_timezone():
    # 14:00 UTC is 10:00 in New York (allowed) even though the org is in London.
    state = _given(timezone="America/New_York")
    assert (
        check_outbound(
            contact=state, channel="call", now=DAYTIME, org_timezone="Europe/London"
        ).allowed
        is True
    )


def test_unknown_timezone_falls_back_to_organization_timezone():
    state = _given(timezone="Not/AZone")
    assert (
        check_outbound(
            contact=state, channel="call", now=DAYTIME, org_timezone="Europe/London"
        ).allowed
        is True
    )


def test_attempt_cap_is_enforced():
    state = _given(attempts_last_24h=2)
    decision = check_outbound(
        contact=state, channel="call", now=DAYTIME, max_attempts_per_day=2
    )
    assert decision.allowed is False
    assert any("limit" in r for r in decision.reasons)


def test_quiet_window_wraps_past_midnight():
    from datetime import time

    assert in_quiet_hours(time(22, 0)) is True
    assert in_quiet_hours(time(7, 59)) is True
    assert in_quiet_hours(time(8, 0)) is False
    assert in_quiet_hours(time(12, 0)) is False

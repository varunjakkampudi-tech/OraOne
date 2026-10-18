"""Human handoff: escalations are persisted, delivered with retry, and never
promise follow-up to a visitor who gave no way to be reached.

The pure tests run everywhere. The database tests run against Postgres, roll
back after each case, and skip when the database is not reachable.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.services import escalation_service
from app.services.rag_answer import HANDOFF_TEXT

# ── pure rules ────────────────────────────────────────────────────────────────


def test_handoff_without_contact_does_not_promise_follow_up():
    reply = escalation_service.handoff_reply(HANDOFF_TEXT, contact_known=False)
    assert "if you share" in reply.lower()
    assert "way to reach you" in reply
    assert reply != HANDOFF_TEXT


def test_handoff_with_contact_keeps_the_team_follow_up_wording():
    assert (
        escalation_service.handoff_reply(HANDOFF_TEXT, contact_known=True)
        == HANDOFF_TEXT
    )


def test_has_contact_requires_a_usable_email_or_phone():
    assert escalation_service.has_contact("pat@example.test", None)
    assert escalation_service.has_contact(None, "+14155550123")
    assert not escalation_service.has_contact(None, None)
    assert not escalation_service.has_contact("   ", "not-a-phone")


def test_alert_body_states_when_no_contact_was_given():
    row = type(
        "Row",
        (),
        {
            "channel": "chat",
            "question": "Do you ship to Goa?",
            "has_contact": False,
            "contact_name": None,
            "contact_email": None,
            "contact_phone": None,
        },
    )()
    body = escalation_service._alert_body(row)
    assert "No contact details given" in body["contact"]


# ── database behaviour ───────────────────────────────────────────────────────


def _postgres_reachable() -> bool:
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


db_only = pytest.mark.skipif(
    not _postgres_reachable(), reason="Postgres is not reachable from this host."
)


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator:
    from app.database import session as db_session_module
    from app.database.session import dispose_engine, init_engine

    await dispose_engine()
    init_engine()
    maker = db_session_module.AsyncSessionLocal
    assert maker is not None
    async with maker() as s:
        yield s
        await s.rollback()
    await dispose_engine()


async def _seed(session, *, with_admin: bool = True):
    from app.core.security import hash_password
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.organization_member import (
        MemberRole,
        MemberStatus,
        OrganizationMember,
    )
    from app.database.models.project import Project, ProjectStatus
    from app.database.models.user import User

    suffix = uuid.uuid4().hex[:8]
    owner = User(
        auth_subject=f"sub-{uuid.uuid4()}",
        email=f"owner-{suffix}@example.test",
        full_name="Owner",
        password_hash=hash_password("not-used-in-this-test-3"),
        is_email_verified=True,
    )
    session.add(owner)
    await session.flush()
    org = Organization(
        name=f"Handoff {suffix}",
        slug=f"handoff-{suffix}",
        plan=OrgPlan.free,
        owner_user_id=owner.id,
    )
    session.add(org)
    await session.flush()
    project = Project(
        organization_id=org.id,
        name="Main",
        slug=f"main-{suffix}",
        is_default=True,
        status=ProjectStatus.active,
    )
    session.add(project)
    await session.flush()
    if with_admin:
        session.add(
            OrganizationMember(
                organization_id=org.id,
                user_id=owner.id,
                role=MemberRole.owner,
                status=MemberStatus.active,
            )
        )
        await session.flush()
    return org, project


async def _open_escalation(session, org, project, **kwargs):
    return await escalation_service.create_escalation(
        session,
        organization_id=org.id,
        project_id=project.id,
        channel="chat",
        question="Do you deliver on Sundays? email me at pat@example.test",
        **kwargs,
    )


@db_only
@pytest.mark.asyncio
async def test_new_handoff_is_stored_pending_with_scrubbed_question(db_session):
    org, project = await _seed(db_session)
    row = await _open_escalation(db_session, org, project, email="pat@example.test")

    assert row.status == "open"
    assert row.notify_status == "pending"
    assert row.has_contact is True
    assert "pat@example.test" not in row.question
    assert "[email]" in row.question


@db_only
@pytest.mark.asyncio
async def test_smtp_unset_leaves_rows_pending_and_spends_no_attempts(
    db_session, monkeypatch
):
    org, project = await _seed(db_session)
    row = await _open_escalation(db_session, org, project)
    monkeypatch.setattr(
        escalation_service.email_service, "delivery_configured", lambda: False
    )

    counts = await escalation_service.deliver_due(db_session)

    assert counts["skipped"] >= 1
    assert row.notify_status == "pending"
    assert row.notify_attempts == 0


@db_only
@pytest.mark.asyncio
async def test_successful_delivery_marks_sent_and_emails_admins(
    db_session, monkeypatch
):
    org, project = await _seed(db_session)
    row = await _open_escalation(db_session, org, project)
    sent: list[dict] = []
    monkeypatch.setattr(
        escalation_service.email_service, "delivery_configured", lambda: True
    )

    def fake_send(**kwargs):
        sent.append(kwargs)
        return True

    monkeypatch.setattr(escalation_service.email_service, "send_email", fake_send)

    counts = await escalation_service.deliver_due(db_session)

    assert counts["sent"] == 1
    assert row.notify_status == "sent"
    assert len(sent) == 1
    assert sent[0]["template"] == "escalation_alert.html"
    assert sent[0]["to"].endswith("@example.test")


@db_only
@pytest.mark.asyncio
async def test_failed_send_backs_off_then_dead_letters(db_session, monkeypatch):
    org, project = await _seed(db_session)
    row = await _open_escalation(db_session, org, project)
    monkeypatch.setattr(
        escalation_service.email_service, "delivery_configured", lambda: True
    )
    monkeypatch.setattr(
        escalation_service.email_service, "send_email", lambda **_: False
    )

    now = datetime.now(timezone.utc)
    await escalation_service.deliver_due(db_session, now=now)
    assert row.notify_status == "failed"
    assert row.notify_attempts == 1
    assert row.last_error == "delivery_failed"
    assert row.next_attempt_at > now

    # Not yet due: nothing is attempted before the backoff window ends.
    await escalation_service.deliver_due(db_session, now=now)
    assert row.notify_attempts == 1

    later = row.next_attempt_at + timedelta(seconds=1)
    for _ in range(escalation_service.MAX_NOTIFY_ATTEMPTS - 1):
        await escalation_service.deliver_due(db_session, now=later)
        later = row.next_attempt_at + timedelta(seconds=1)
    assert row.notify_attempts == escalation_service.MAX_NOTIFY_ATTEMPTS
    assert row.notify_status == "dead_letter"


@db_only
@pytest.mark.asyncio
async def test_no_admins_is_reported_not_silently_dropped(db_session, monkeypatch):
    org, project = await _seed(db_session, with_admin=False)
    row = await _open_escalation(db_session, org, project)
    monkeypatch.setattr(
        escalation_service.email_service, "delivery_configured", lambda: True
    )

    counts = await escalation_service.deliver_due(db_session)

    assert counts["no_recipients"] == 1
    assert row.notify_status == "no_recipients"


@db_only
@pytest.mark.asyncio
async def test_escalations_are_scoped_to_their_project(db_session):
    org, project = await _seed(db_session)
    await _open_escalation(db_session, org, project)

    rows = (
        (
            await db_session.execute(
                select(escalation_service.Escalation).where(
                    escalation_service.Escalation.project_id == uuid.uuid4()
                )
            )
        )
        .scalars()
        .all()
    )
    assert rows == []

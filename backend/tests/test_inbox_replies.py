"""Staff replies reach the customer's channel, and the reply is recorded honestly.

Database-backed: each test seeds an organization, project, agent, conversation and escalation, then
calls the reply route as a team member. The channel sender is a fake, so no message leaves the test.
Skips when Postgres is not reachable.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import HTTPException


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


# Probe once at import time: inside a running test event loop the probe cannot start its own loop.
_DB_REACHABLE = _postgres_reachable()
db_only = pytest.mark.skipif(
    not _DB_REACHABLE, reason="Postgres is not reachable from this host."
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


class _Sender:
    """Records calls. ``error`` is raised instead of sending when given."""

    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls: list[dict] = []

    async def send(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return {"id": "provider-msg-1"}


async def _seed(
    session, *, channel: str, phone: str | None, other_project: bool = False
):
    from app.core.security import hash_password
    from app.database.models.agent import Agent, AgentStatus, AgentType
    from app.database.models.conversation import (
        Conversation,
        ConversationChannel,
        ConversationStatus,
    )
    from app.database.models.escalation import Escalation
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.organization_member import (
        MemberRole,
        MemberStatus,
        OrganizationMember,
    )
    from app.database.models.project import Project, ProjectStatus
    from app.database.models.user import User

    suffix = uuid.uuid4().hex[:8]
    admin = User(
        auth_subject=f"sub-inbox-{suffix}",
        email=f"inbox-{suffix}@example.test",
        full_name="Team Member",
        password_hash=hash_password("not-used-in-this-test-13"),
        is_email_verified=True,
    )
    session.add(admin)
    await session.flush()
    org = Organization(
        name=f"Inbox {suffix}",
        slug=f"inbox-{suffix}",
        plan=OrgPlan.free,
        owner_user_id=admin.id,
    )
    session.add(org)
    await session.flush()
    project = Project(
        organization_id=org.id,
        name="Main",
        slug=f"inbox-main-{suffix}",
        is_default=True,
        status=ProjectStatus.active,
    )
    session.add(project)
    await session.flush()
    session.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=admin.id,
            role=MemberRole.admin,
            status=MemberStatus.active,
        )
    )
    agent = Agent(
        organization_id=org.id,
        project_id=project.id,
        name="Support",
        type=AgentType.chat,
        status=AgentStatus.active,
        model="test/model",
    )
    session.add(agent)
    await session.flush()
    conversation_project = project
    if other_project:
        conversation_project = Project(
            organization_id=org.id,
            name="Other",
            slug=f"inbox-other-{suffix}",
            is_default=False,
            status=ProjectStatus.active,
        )
        session.add(conversation_project)
        await session.flush()
    conversation = Conversation(
        organization_id=org.id,
        project_id=conversation_project.id,
        agent_id=agent.id,
        channel=ConversationChannel(channel),
        status=ConversationStatus.active,
        started_at=datetime.now(timezone.utc),
        customer_phone=phone,
    )
    session.add(conversation)
    await session.flush()
    escalation = Escalation(
        organization_id=org.id,
        project_id=conversation_project.id,
        conversation_id=conversation.id,
        channel=channel,
        question="Can someone call me back?",
        status="open",
        notify_status="sent",
        notify_attempts=0,
        next_attempt_at=datetime.now(timezone.utc),
        due_at=datetime.now(timezone.utc),
    )
    session.add(escalation)
    await session.commit()
    ctx = SimpleNamespace(user_id=admin.id, organization_id=org.id)
    pctx = SimpleNamespace(organization_id=org.id, project_id=project.id)
    return conversation, escalation, ctx, pctx


async def _reply(session, conversation, ctx, pctx, sender, text="Happy to help."):
    from app.api.inbox import routes as inbox

    return await inbox.reply_to_conversation(
        conversation_id=conversation.id,
        payload=inbox.ReplyRequest(text=text),
        ctx=ctx,
        pctx=pctx,
        session=session,
        sender=sender,
    )


@db_only
@pytest.mark.asyncio
async def test_a_chat_reply_is_delivered_in_the_thread_and_records_the_first_reply(
    db_session,
):
    conversation, escalation, ctx, pctx = await _seed(
        db_session, channel="chat", phone=None
    )
    sender = _Sender()

    result = await _reply(db_session, conversation, ctx, pctx, sender)

    assert result.delivery == "delivered"
    assert sender.calls == []  # website chat never goes through the external sender
    await db_session.refresh(escalation)
    assert escalation.first_reply_at is not None
    assert escalation.status == "open"  # replying does not resolve the item


@db_only
@pytest.mark.asyncio
async def test_a_whatsapp_reply_is_sent_to_the_customers_number(db_session):
    conversation, escalation, ctx, pctx = await _seed(
        db_session, channel="whatsapp", phone="+14155550123"
    )
    sender = _Sender()

    result = await _reply(db_session, conversation, ctx, pctx, sender)

    assert result.delivery == "sent"
    assert sender.calls[0]["channel"] == "whatsapp"
    assert sender.calls[0]["recipient"] == "+14155550123"
    await db_session.refresh(escalation)
    assert escalation.first_reply_at is not None


@db_only
@pytest.mark.asyncio
async def test_an_unconfigured_channel_is_reported_and_not_counted_as_a_reply(
    db_session,
):
    from app.services.workflow_senders import OutboundNotConfigured

    conversation, escalation, ctx, pctx = await _seed(
        db_session, channel="sms", phone="+14155550199"
    )
    sender = _Sender(
        error=OutboundNotConfigured(
            "No enabled sms channel is set up for this organization."
        )
    )

    result = await _reply(db_session, conversation, ctx, pctx, sender)

    assert result.delivery == "not_configured"
    await db_session.refresh(escalation)
    assert escalation.first_reply_at is None


@db_only
@pytest.mark.asyncio
async def test_a_provider_failure_is_reported_without_provider_detail(db_session):
    conversation, _escalation, ctx, pctx = await _seed(
        db_session, channel="sms", phone="+14155550111"
    )
    sender = _Sender(error=RuntimeError("provider 500 with secret token abc123"))

    result = await _reply(db_session, conversation, ctx, pctx, sender)

    assert result.delivery == "failed"
    assert "abc123" not in (result.reason or "")


@db_only
@pytest.mark.asyncio
async def test_a_customer_without_an_address_is_not_sent_to(db_session):
    conversation, _escalation, ctx, pctx = await _seed(
        db_session, channel="whatsapp", phone=None
    )
    sender = _Sender()

    result = await _reply(db_session, conversation, ctx, pctx, sender)

    assert result.delivery == "not_configured"
    assert sender.calls == []


@db_only
@pytest.mark.asyncio
async def test_a_conversation_in_another_project_is_not_found(db_session):
    conversation, _escalation, ctx, pctx = await _seed(
        db_session, channel="chat", phone=None, other_project=True
    )

    with pytest.raises(HTTPException) as exc:
        await _reply(db_session, conversation, ctx, pctx, _Sender())
    assert exc.value.status_code == 404

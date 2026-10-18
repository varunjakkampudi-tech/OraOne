"""Do-not-call list, STOP-reply opt-outs and voice conversation channel.

Unit tests need no database. Database tests (HTTP round trips, cross-organization
isolation, campaign planning and dial-time checks, STOP replies, voice turns) need
live Postgres and are skipped when it is unreachable, like test_outbound_calls.py.
No test contacts Twilio or the AI model: calls are faked and ``answer_query`` is
replaced with a stub that records whether it ran.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import select

from app.database.models.agent_channel import ChannelType
from app.database.models.conversation import ConversationChannel
from app.database.models.do_not_contact import ContactScope, ContactSource, DoNotContact
from app.services import contact_policy_service as cp
from app.services import omnichannel_service
from app.services.calls import campaign_service as svc

from app.services.outreach_policy import ContactState, check_outbound

DAYTIME = datetime(2026, 10, 17, 14, 0, tzinfo=timezone.utc)
PUBLIC_BASE = "https://api.example.test"
ACCOUNT_SID = "AC00000000000000000000000000000000"
TWILIO_NUMBER = "+15550001111"
PHONE = "+14155550123"
EMAIL = "Jane.Doe@Example.com"


def _cfg(**overrides):
    base = {
        "twilio_account_sid": ACCOUNT_SID,
        "twilio_auth_token": "contact-policy-test-token",
        "twilio_phone_number": TWILIO_NUMBER,
        "public_api_base_url": PUBLIC_BASE,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _lead(*, phone=PHONE, email=None, consent="granted", **extra):
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        phone=phone,
        email=email,
        extra={"consent": consent, **extra},
    )


# ───────────────────────────── unit: rules and values ─────────────────────────────


@pytest.mark.parametrize(
    "text",
    ["STOP", "stop!", "  Unsubscribe. ", "opt out", "Opt-Out", "STOP ALL", "stopall"],
)
def test_stop_style_replies_are_opt_outs(text):
    assert cp.is_opt_out_message(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "",
        None,
        "please stop calling my boss",
        "stopping by tomorrow",
        "hello",
        "cancel my order",
    ],
)
def test_ordinary_messages_are_not_opt_outs(text):
    assert cp.is_opt_out_message(text) is False


def test_user_entries_are_normalised_and_bad_ones_refused():
    assert cp.normalise_entry_value(EMAIL) == "jane.doe@example.com"
    assert cp.normalise_entry_value("+1 (415) 555-0123") == PHONE
    for bad in ["4155550123", "not a number", "", "jane@", "+12"]:
        with pytest.raises(cp.ContactEntryError):
            cp.normalise_entry_value(bad)


def test_suppression_scope_matching_rules():
    assert cp._scopes_for("call") == (ContactScope.all, "call")
    assert cp._scopes_for("voice") == (ContactScope.all,)


def test_channel_enums_include_voice():
    assert ConversationChannel("voice") is ConversationChannel.voice
    assert "voice" in ChannelType.ALL


def test_suppressed_lead_is_refused_by_the_call_policy_with_plain_reason():
    lead = _lead()
    decision = svc.evaluate_lead(
        lead, attempts_last_24h=0, now=DAYTIME, org_timezone="UTC", suppressed=True
    )
    assert decision.allowed is False
    assert any("do-not-contact" in r for r in decision.reasons)


def test_unsuppressed_consenting_lead_is_still_allowed():
    decision = svc.evaluate_lead(
        _lead(), attempts_last_24h=0, now=DAYTIME, org_timezone="UTC"
    )
    assert decision.allowed is True


def test_legacy_lead_extra_flag_still_suppresses():
    lead = _lead(suppressed=True)
    decision = svc.evaluate_lead(
        lead, attempts_last_24h=0, now=DAYTIME, org_timezone="UTC"
    )
    assert decision.allowed is False


def test_outreach_policy_stays_pure_and_honours_the_flag():
    state = ContactState(consent="given", suppressed=True)
    assert check_outbound(contact=state, channel="sms", now=DAYTIME).allowed is False


# ───────────────────────────── database helpers ─────────────────────────────


def _postgres_reachable() -> bool:
    import asyncio
    import os

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


REQUIRES_DB = pytest.mark.skipif(
    not _postgres_reachable(),
    reason="Postgres is not reachable from this host (private VPC, etc).",
)


@pytest_asyncio.fixture
async def db_session():
    from app.database import session as db_session_module
    from app.database.session import dispose_engine, init_engine

    await dispose_engine()
    init_engine()
    Maker = db_session_module.AsyncSessionLocal
    assert Maker is not None
    async with Maker() as s:
        # Keep loaded attributes readable after commit (no lazy refresh in async code).
        s.sync_session.expire_on_commit = False
        yield s
        await s.rollback()
    await dispose_engine()


async def _seed_org(session, *, slug_hint: str):
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.organization_member import (
        MemberRole,
        MemberStatus,
        OrganizationMember,
    )
    from app.database.models.project import Project
    from app.database.models.user import User

    user = User(
        auth_subject=f"sub-{uuid.uuid4()}",
        email=f"{slug_hint}-{uuid.uuid4().hex[:8]}@x.com",
        full_name=slug_hint.title(),
    )
    session.add(user)
    await session.flush()
    org = Organization(
        name=f"{slug_hint.title()} Workspace",
        slug=f"{slug_hint}-{uuid.uuid4().hex[:8]}",
        plan=OrgPlan.free,
        owner_user_id=user.id,
    )
    session.add(org)
    await session.flush()
    session.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=MemberRole.owner,
            status=MemberStatus.active,
            joined_at=datetime.now(timezone.utc),
        )
    )
    project = Project(
        organization_id=org.id,
        name="Default",
        slug="default",
        is_default=True,
        created_by_user_id=user.id,
    )
    session.add(project)
    await session.flush()
    return user, org, project


async def _add_lead(
    session, *, org, project, phone=PHONE, email=None, consent="granted"
):
    from app.database.models.lead import Lead

    lead = Lead(
        organization_id=org.id,
        project_id=project.id,
        name=f"Lead {uuid.uuid4().hex[:6]}",
        phone=phone,
        email=email,
        source="import",
        extra={"consent": consent},
    )
    session.add(lead)
    await session.flush()
    return lead


async def _add_agent(session, *, org, project):
    from app.database.models.agent import Agent, AgentStatus, AgentType

    agent = Agent(
        organization_id=org.id,
        project_id=project.id,
        name="Front desk",
        type=AgentType.chat,
        status=AgentStatus.active,
        model="google/gemini-2.5-flash",
    )
    session.add(agent)
    await session.flush()
    return agent


async def _cleanup(session, *, org_ids, user_ids) -> None:
    from sqlalchemy import delete

    from app.database.models.call_campaign import CallAttempt, CallCampaign
    from app.database.models.conversation import Conversation
    from app.database.models.do_not_contact import DoNotContact
    from app.database.models.lead import Lead
    from app.database.models.organization import Organization
    from app.database.models.organization_member import OrganizationMember
    from app.database.models.project import Project
    from app.database.models.user import User

    await session.rollback()
    await session.execute(
        delete(DoNotContact).where(DoNotContact.organization_id.in_(org_ids))
    )
    await session.execute(
        delete(CallAttempt).where(CallAttempt.organization_id.in_(org_ids))
    )
    await session.execute(
        delete(CallCampaign).where(CallCampaign.organization_id.in_(org_ids))
    )
    await session.execute(
        delete(Conversation).where(Conversation.organization_id.in_(org_ids))
    )
    await session.execute(delete(Lead).where(Lead.organization_id.in_(org_ids)))
    await session.execute(delete(Project).where(Project.organization_id.in_(org_ids)))
    await session.execute(
        delete(OrganizationMember).where(
            OrganizationMember.organization_id.in_(org_ids)
        )
    )
    await session.execute(delete(Organization).where(Organization.id.in_(org_ids)))
    await session.execute(delete(User).where(User.id.in_(user_ids)))
    await session.commit()


def _ctx(user, org):
    from app.middleware.org_context import OrgContext

    return OrgContext(
        user_id=user.id,
        auth_subject=f"sub-{org.id}",
        organization_id=org.id,
        membership_role="owner",
    )


async def _real_session():
    """The API's own session dependency, so route handlers use the test database."""
    from app.database import session as db_session_module

    async with db_session_module.AsyncSessionLocal() as s:
        yield s


def _contact_app(current: dict):
    from app.api.contact_policy import router
    from app.database.session import get_db
    from app.middleware.org_context import get_current_organization

    app = FastAPI()
    app.include_router(router)

    async def _override():
        return current["ctx"]

    app.dependency_overrides[get_current_organization] = _override
    app.dependency_overrides[get_db] = _real_session
    return app


# ───────────────────────────── database: list, add, remove ─────────────────────────────


@REQUIRES_DB
@pytest.mark.asyncio
async def test_add_list_remove_round_trip_and_duplicate_is_idempotent(db_session):
    from httpx import ASGITransport, AsyncClient

    user, org, _ = await _seed_org(db_session, slug_hint="dncrt")
    user_id, org_id = user.id, org.id
    await db_session.commit()
    current = {"ctx": _ctx(user, org)}
    app = _contact_app(current)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            created = await client.post(
                "/api/contact-policy/do-not-contact",
                json={
                    "value": "+1 (415) 555-0123",
                    "channel_scope": "call",
                    "reason": "asked",
                },
            )
            assert created.status_code == 201, created.text
            entry = created.json()
            assert entry["value"] == PHONE
            assert entry["source"] == ContactSource.user
            assert entry["channel_scope"] == "call"

            listing = (await client.get("/api/contact-policy/do-not-contact")).json()
            assert [e["id"] for e in listing] == [entry["id"]]

            again = await client.post(
                "/api/contact-policy/do-not-contact",
                json={"value": PHONE, "channel_scope": "call"},
            )
            assert again.status_code == 200
            assert again.json()["id"] == entry["id"]

            removed = await client.delete(
                f"/api/contact-policy/do-not-contact/{entry['id']}"
            )
            assert removed.status_code == 204
            assert (await client.get("/api/contact-policy/do-not-contact")).json() == []

            bad = await client.post(
                "/api/contact-policy/do-not-contact", json={"value": "4155550123"}
            )
            assert bad.status_code == 422
    finally:
        await _cleanup(db_session, org_ids=[org_id], user_ids=[user_id])


@REQUIRES_DB
@pytest.mark.asyncio
async def test_do_not_contact_entries_are_isolated_per_organization(db_session):
    from httpx import ASGITransport, AsyncClient

    user_a, org_a, project_a = await _seed_org(db_session, slug_hint="dnca")
    user_b, org_b, project_b = await _seed_org(db_session, slug_hint="dncb")
    lead_b = await _add_lead(db_session, org=org_b, project=project_b, phone=PHONE)
    await db_session.commit()

    current = {"ctx": _ctx(user_a, org_a)}
    app = _contact_app(current)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            made = await client.post(
                "/api/contact-policy/do-not-contact",
                json={"value": PHONE, "channel_scope": "all"},
            )
            assert made.status_code == 201, made.text
            entry_id = made.json()["id"]

            # Org B cannot see or delete Org A's entry.
            current["ctx"] = _ctx(user_b, org_b)
            assert (await client.get("/api/contact-policy/do-not-contact")).json() == []
            hidden = await client.delete(
                f"/api/contact-policy/do-not-contact/{entry_id}"
            )
            assert hidden.status_code == 404

            # Org A's entry does not suppress Org B's lead with the same number.
            assert (
                await cp.is_lead_suppressed(db_session, lead=lead_b, channel="call")
                is False
            )

            # Org B's own list is separate: adding the same number there is allowed.
            own = await client.post(
                "/api/contact-policy/do-not-contact",
                json={"value": PHONE, "channel_scope": "all"},
            )
            assert own.status_code == 201
            assert own.json()["id"] != entry_id

            current["ctx"] = _ctx(user_a, org_a)
            listing = (await client.get("/api/contact-policy/do-not-contact")).json()
            assert [e["id"] for e in listing] == [entry_id]
    finally:
        await _cleanup(
            db_session, org_ids=[org_a.id, org_b.id], user_ids=[user_a.id, user_b.id]
        )


# ───────────────────────────── database: planning and dial-time ─────────────────────────────


@pytest.fixture
def calling_configured(monkeypatch):
    monkeypatch.setattr(svc, "get_channels_config", lambda: _cfg())
    monkeypatch.setattr(svc, "_now", lambda: DAYTIME)


@REQUIRES_DB
@pytest.mark.asyncio
async def test_campaign_planning_refuses_a_do_not_call_number(
    db_session, calling_configured
):
    user, org, project = await _seed_org(db_session, slug_hint="dncplan")
    listed = await _add_lead(db_session, org=org, project=project, phone=PHONE)
    clear = await _add_lead(db_session, org=org, project=project, phone="+14155550199")
    db_session.add(
        DoNotContact(
            id=uuid.uuid4(),
            organization_id=org.id,
            normalised_value=PHONE,
            channel_scope=ContactScope.call,
            reason="asked",
            source=ContactSource.user,
        )
    )
    await db_session.commit()
    try:
        campaign = await svc.create_campaign(
            db_session,
            organization_id=org.id,
            project_id=project.id,
            created_by=user.id,
            name="Plan",
            timezone_name="UTC",
            leads=[listed, clear],
            now=DAYTIME,
        )
        await db_session.commit()
        from app.database.models.call_campaign import CallAttempt

        rows = (
            await db_session.scalars(
                select(CallAttempt).where(CallAttempt.campaign_id == campaign.id)
            )
        ).all()
        by_lead = {r.lead_id: r for r in rows}
        assert by_lead[listed.id].status == "skipped"
        assert "do-not-contact" in by_lead[listed.id].skip_reason
        assert by_lead[clear.id].status == "queued"
    finally:
        await _cleanup(db_session, org_ids=[org.id], user_ids=[user.id])


@REQUIRES_DB
@pytest.mark.asyncio
async def test_dial_time_check_skips_a_number_listed_after_planning(
    db_session, calling_configured, monkeypatch
):
    from app.database.models.call_campaign import (
        AttemptStatus,
        CallAttempt,
        CampaignStatus,
    )

    placed: list[str] = []

    async def fake_place_call(attempt, *, to_number):
        placed.append(to_number)
        return "CA" + "0" * 32

    monkeypatch.setattr(svc, "place_call", fake_place_call)

    user, org, project = await _seed_org(db_session, slug_hint="dncdial")
    lead = await _add_lead(db_session, org=org, project=project, phone=PHONE)
    campaign = await svc.create_campaign(
        db_session,
        organization_id=org.id,
        project_id=project.id,
        created_by=user.id,
        name="Dial",
        timezone_name="UTC",
        leads=[lead],
        now=DAYTIME,
    )
    campaign.status = CampaignStatus.running
    db_session.add(
        DoNotContact(
            id=uuid.uuid4(),
            organization_id=org.id,
            normalised_value=PHONE,
            channel_scope=ContactScope.all,
            reason="stop",
            source=ContactSource.opt_out_reply,
        )
    )
    await db_session.commit()
    campaign_id = campaign.id
    try:
        result = await svc.dial_next(db_session, campaign_id=campaign_id, now=DAYTIME)
        assert result is None
        assert placed == []
        attempt = await db_session.scalar(
            select(CallAttempt).where(CallAttempt.campaign_id == campaign_id)
        )
        await db_session.refresh(attempt)
        assert attempt.status == AttemptStatus.skipped
        assert "do-not-contact" in attempt.skip_reason
    finally:
        await _cleanup(db_session, org_ids=[org.id], user_ids=[user.id])


# ───────────────────────────── database: STOP replies and voice ─────────────────────────────


@REQUIRES_DB
@pytest.mark.asyncio
async def test_stop_reply_records_an_opt_out_on_any_channel_and_sends_no_reply(
    db_session, monkeypatch
):
    from sqlalchemy import func

    from app.database.models.conversation import Conversation
    from app.database.models.message import Message, MessageSender

    answered: list[str] = []

    async def fake_answer(*args, **kwargs):
        answered.append(True)
        return {"answer": "should never be sent", "grounded": True, "confidence": 1.0}

    monkeypatch.setattr(omnichannel_service, "answer_query", fake_answer)

    user, org, project = await _seed_org(db_session, slug_hint="stopreply")
    agent = await _add_agent(db_session, org=org, project=project)
    await db_session.commit()
    try:
        reply = await omnichannel_service.handle_inbound(
            db_session,
            omnichannel_service.InboundMessage(
                channel="sms",
                organization_id=org.id,
                agent_id=agent.id,
                project_id=project.id,
                text="STOP",
                phone=PHONE,
            ),
        )
        await db_session.commit()

        assert reply.handled is False
        assert reply.text == ""
        assert reply.opted_out is True
        assert answered == []

        entries = (
            await db_session.scalars(
                select(cp.DoNotContact).where(cp.DoNotContact.organization_id == org.id)
            )
        ).all()
        assert [(e.normalised_value, e.channel_scope, e.source) for e in entries] == [
            (PHONE, ContactScope.all, ContactSource.opt_out_reply)
        ]

        agent_messages = await db_session.scalar(
            select(func.count(Message.id))
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Conversation.organization_id == org.id)
            .where(Message.sender == MessageSender.agent)
        )
        assert agent_messages == 0

        # The opt-out applies on other channels too.
        assert (
            await cp.is_suppressed(
                db_session, organization_id=org.id, values=[PHONE], channel="whatsapp"
            )
            is True
        )
    finally:
        await _cleanup(db_session, org_ids=[org.id], user_ids=[user.id])


@REQUIRES_DB
@pytest.mark.asyncio
async def test_voice_turn_is_recorded_on_the_voice_channel(db_session, monkeypatch):
    from httpx import ASGITransport, AsyncClient

    from app.api.voice import routes as voice_routes
    from app.database.models.conversation import Conversation
    from app.database.session import get_db

    async def fake_answer(*args, **kwargs):
        return {
            "answer": "Our opening hours are nine to five.",
            "grounded": True,
            "confidence": 0.9,
        }

    monkeypatch.setattr(omnichannel_service, "answer_query", fake_answer)
    monkeypatch.setattr(voice_routes, "_is_signed", lambda request, form: True)
    monkeypatch.setattr(
        voice_routes,
        "get_channels_config",
        lambda: _cfg(voice_say_voice=None, voice_handoff_number=None),
    )

    user, org, project = await _seed_org(db_session, slug_hint="voicechan")
    agent = await _add_agent(db_session, org=org, project=project)
    await db_session.commit()
    org_id = org.id
    binding = SimpleNamespace(
        organization_id=org_id, agent_id=agent.id, project_id=project.id
    )

    async def fake_resolve(db, business_number):
        return binding

    monkeypatch.setattr(voice_routes, "_resolve_binding", fake_resolve)

    app = FastAPI()
    app.include_router(voice_routes.router)
    app.dependency_overrides[get_db] = _real_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/voice/gather",
                data={
                    "To": TWILIO_NUMBER,
                    "From": "+447700900123",
                    "CallSid": "CA" + "1" * 32,
                    "SpeechResult": "What are your opening hours?",
                },
            )
            assert resp.status_code == 200
            assert "nine to five" in resp.text

            stop = await client.post(
                "/api/voice/gather",
                data={
                    "To": TWILIO_NUMBER,
                    "From": "+447700900123",
                    "CallSid": "CA" + "2" * 32,
                    "SpeechResult": "stop",
                },
            )
            assert stop.status_code == 200
            assert "<Hangup" in stop.text
            assert voice_routes.twiml.OPT_OUT_TEXT in stop.text

        await db_session.rollback()
        channels = (
            await db_session.scalars(
                select(Conversation.channel).where(
                    Conversation.organization_id == org_id
                )
            )
        ).all()
        assert channels and all(c == ConversationChannel.voice for c in channels)
    finally:
        await _cleanup(db_session, org_ids=[org_id], user_ids=[user.id])


@pytest.fixture(autouse=True)
def _default_project_for_tests(monkeypatch):
    """Customer paths resolve a project. These tests have no project rows, so
    the organization default is pinned to one fixed project."""
    from app.services import project_scope

    project = uuid.uuid4()

    async def _default(_session, _organization_id):
        return project

    monkeypatch.setattr(project_scope, "default_project_id", _default)

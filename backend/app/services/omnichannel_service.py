"""Omnichannel message pipeline (Phase M) — one AI across every channel.

This is the single inbound→answer→memory path shared by **all** text/messaging
surfaces (WhatsApp, SMS, Email, Messenger, Instagram, Telegram, Slack, Teams,
Mobile/Desktop SDK). It deliberately reuses the exact same building blocks the
website chat already uses — :func:`answer_query` (RAG) and
:mod:`app.services.visitor_service` (cross-channel identity + shared memory) —
so there is never a second "AI" to maintain.

The unification promise ("a customer starts on the website, continues on
WhatsApp, calls support, replies to email — everything stays one conversation")
is delivered by the :class:`VisitorProfile`: every channel resolves the SAME
profile (by phone / email / handle) and contributes to one rolling memory, so
the agent always knows who it is talking to regardless of surface.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent, AgentStatus
from app.database.models.channel_inbound_receipt import ChannelInboundReceipt
from app.database.models.conversation import (
    Conversation,
    ConversationChannel,
    ConversationStatus,
)
from app.database.models.message import Message, MessageSender
from app.services import contact_policy_service, visitor_service, workflow_triggers
from app.services.rag_answer import answer_query

log = logging.getLogger("app.omnichannel")

# Reuse (rather than start a new) conversation thread for the same person on
# the same channel when the last activity is within this window.
_THREAD_WINDOW = timedelta(hours=24)

_AGENT_UNAVAILABLE = (
    "Thanks for your message! Our assistant is briefly unavailable — "
    "we'll get back to you shortly."
)


@dataclass
class InboundMessage:
    """A provider-agnostic inbound message, produced by a channel adapter."""

    channel: str  # "whatsapp", "sms", "telegram", …
    organization_id: uuid.UUID
    agent_id: uuid.UUID
    text: str
    project_id: Optional[uuid.UUID] = None
    # Sender identity — whichever the channel knows.
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    handle: Optional[str] = None  # @username, page-scoped id, …
    external_id: Optional[str] = None  # provider's stable user id
    external_thread_id: Optional[str] = None  # provider conversation id
    # Provider's namespaced message id (e.g. "telegram:123"); redeliveries are dropped.
    provider_message_id: Optional[str] = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutboundReply:
    """The agent's reply, ready for the adapter to deliver back to the user."""

    text: str
    conversation_id: Optional[uuid.UUID] = None
    grounded: bool = False
    confidence: float = 0.0
    # False when the reply is a fallback. Recorded on the message metadata only; the text is sent as-is.
    generated: bool = False
    handled: bool = True
    # True when the message was a STOP-style opt-out: no AI reply is sent.
    opted_out: bool = False


def _channel_enum(channel: str) -> ConversationChannel:
    try:
        return ConversationChannel(channel)
    except ValueError:
        return ConversationChannel.chat


def _visitor_key(msg: InboundMessage) -> str:
    """Pick the most *unifying* resolution key so this person collapses onto
    the same profile they use elsewhere (phone ties to WhatsApp/SMS; email to chat)."""
    phone = visitor_service.normalize_phone(msg.phone)
    if phone:
        return phone
    email = visitor_service.normalize_email(msg.email)
    if email:
        return email
    if msg.external_id:
        return f"{msg.channel}:{msg.external_id}"
    if msg.handle:
        return f"{msg.channel}:{msg.handle}"
    return f"{msg.channel}:{uuid.uuid4().hex[:16]}"


async def _find_or_create_thread(
    session: AsyncSession,
    msg: InboundMessage,
    profile,
    channel_enum: ConversationChannel,
) -> Conversation:
    """Continue the visitor's recent thread on this channel, or open a new one."""
    conversation: Optional[Conversation] = None
    if profile is not None:
        conversation = await session.scalar(
            select(Conversation)
            .where(Conversation.organization_id == msg.organization_id)
            .where(Conversation.agent_id == msg.agent_id)
            .where(Conversation.channel == channel_enum)
            .where(Conversation.visitor_profile_id == profile.id)
            .where(Conversation.status == ConversationStatus.active)
            .where(Conversation.deleted_at.is_(None))
            .order_by(Conversation.last_message_at.desc().nullslast())
            .limit(1)
        )
        if conversation is not None and conversation.last_message_at is not None:
            if (
                visitor_service.now_utc() - conversation.last_message_at
                > _THREAD_WINDOW
            ):
                conversation = None  # too stale — start fresh

    if conversation is None:
        conversation = Conversation(
            organization_id=msg.organization_id,
            project_id=msg.project_id,
            agent_id=msg.agent_id,
            channel=channel_enum,
            status=ConversationStatus.active,
            title=(msg.text[:60] or f"{msg.channel} chat"),
            started_at=visitor_service.now_utc(),
            customer_name=msg.name,
            customer_email=visitor_service.normalize_email(msg.email),
            customer_phone=visitor_service.normalize_phone(msg.phone),
            extra={
                "source": msg.channel,
                "external_thread_id": msg.external_thread_id,
                "handle": msg.handle,
            },
        )
        session.add(conversation)
        await session.flush()
    return conversation


async def _claim_provider_message(session: AsyncSession, msg: InboundMessage) -> bool:
    """Record the provider's message id for this agent. False means it was already seen.

    The unique insert runs in a savepoint, so a duplicate rolls back only this insert.
    A first delivery that later fails keeps no receipt (the outer transaction rolls back),
    so the provider's retry is still processed.
    """
    if not msg.provider_message_id:
        return True
    try:
        async with session.begin_nested():
            session.add(
                ChannelInboundReceipt(
                    organization_id=msg.organization_id,
                    agent_id=msg.agent_id,
                    message_key=msg.provider_message_id[:255],
                )
            )
            await session.flush()
    except IntegrityError:
        return False
    return True


async def handle_inbound(session: AsyncSession, msg: InboundMessage) -> OutboundReply:
    """Resolve identity → thread → answer (RAG) → persist → share memory.

    Returns the reply text for the adapter to send back. Memory/identity flows
    through the SAME :class:`VisitorProfile` the website chat and messaging channels use, so
    the agent carries context across every channel.
    """
    text = (msg.text or "").strip()
    if not text:
        return OutboundReply(text="", handled=False)

    # A redelivered provider webhook gets no second turn and no second reply.
    if not await _claim_provider_message(session, msg):
        log.info("duplicate inbound ignored channel=%s", msg.channel)
        return OutboundReply(text="", handled=False)

    # Agent must be active — a paused agent never invokes the model.
    agent_status = await session.scalar(
        select(Agent.status).where(Agent.id == msg.agent_id)
    )
    if agent_status is not None and agent_status != AgentStatus.active:
        return OutboundReply(text=_AGENT_UNAVAILABLE, handled=True)

    channel_enum = _channel_enum(msg.channel)

    # 1) Cross-channel identity + shared memory (Phase C).
    profile = await visitor_service.upsert_profile(
        session,
        organization_id=msg.organization_id,
        visitor_key=_visitor_key(msg),
        channel=msg.channel,
        name=msg.name,
        email=msg.email,
        phone=msg.phone,
        context={k: v for k, v in (msg.meta or {}).items() if v is not None},
    )

    # 2) Thread into one conversation per visitor per channel.
    conversation = await _find_or_create_thread(session, msg, profile, channel_enum)
    visitor_service.link_conversation(profile, conversation, channel=msg.channel)
    digest = visitor_service.build_memory_digest(profile, current_channel=msg.channel)

    # 3) Persist the customer's message, then let workflows see it.
    customer_message = Message(
        conversation_id=conversation.id,
        sender=MessageSender.customer,
        message=text,
    )
    session.add(customer_message)
    await session.flush()

    # 3b) STOP-style reply on any channel: record the opt-out and send no AI reply.
    # Runs before workflows so no automation answers the contact after they opted out.
    if contact_policy_service.is_opt_out_message(text):
        added = await contact_policy_service.record_opt_out(
            session,
            organization_id=msg.organization_id,
            values=[msg.phone, msg.email],
            reason=f"STOP reply on {msg.channel}",
        )
        if not (msg.phone or msg.email):
            log.warning("opt-out on %s with no phone or email to record", msg.channel)
        log.info("opt_out_recorded channel=%s entries_added=%s", msg.channel, added)
        conversation.last_message_at = visitor_service.now_utc()
        return OutboundReply(
            text="",
            conversation_id=conversation.id,
            handled=False,
            opted_out=True,
        )

    await workflow_triggers.fire_message_received(
        session,
        organization_id=msg.organization_id,
        project_id=msg.project_id,
        conversation_id=conversation.id,
        message_id=customer_message.id,
    )

    # 4) Generate via the SAME RAG answer pipeline the website chat uses.
    result = await answer_query(
        session,
        text,
        msg.organization_id,
        top_k=5,
        extra_context=digest,
    )
    answer = result.get("answer", "")

    # 5) Persist the agent's reply + roll memory forward.
    session.add(
        Message(
            conversation_id=conversation.id,
            sender=MessageSender.agent,
            message=answer,
            metadata_={
                "grounded": result.get("grounded"),
                "confidence": result.get("confidence"),
                "model": result.get("model"),
                "channel": msg.channel,
                "generated": bool(result.get("generated", False)),
            },
        )
    )
    conversation.last_message_at = visitor_service.now_utc()
    visitor_service.append_memory(profile, channel=msg.channel, role="user", text=text)
    visitor_service.append_memory(
        profile, channel=msg.channel, role="assistant", text=answer
    )

    return OutboundReply(
        text=answer,
        conversation_id=conversation.id,
        grounded=bool(result.get("grounded")),
        confidence=float(result.get("confidence") or 0.0),
        generated=bool(result.get("generated", False)),
        handled=True,
    )

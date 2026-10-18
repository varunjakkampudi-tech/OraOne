"""Staff replies to a customer conversation.

A reply is stored first, so the team and the customer always see it in the thread. It is then
delivered on the conversation's channel. The result says what happened: "delivered" (website chat,
which the visitor reads in the thread), "sent" (the provider accepted it), "not_configured" (the
channel is not set up or the customer has no address on it) or "failed". The reply is never
reported as sent unless the provider accepted it.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission
from app.database.models.conversation import Conversation, ConversationChannel
from app.database.models.message import Message, MessageSender
from app.database.session import get_db
from app.middleware.org_context import OrgContext
from app.middleware.project_context import ProjectContext, get_current_project
from app.services import escalation_service
from app.services.authorization import require_permission
from app.services.workflow_senders import ChannelOutboundSender, OutboundNotConfigured

log = logging.getLogger("app.inbox")

router = APIRouter(prefix="/api/inbox", tags=["inbox"])

# Channels that deliver to a customer address stored on the conversation.
_ADDRESS_FIELD = {
    ConversationChannel.whatsapp: "customer_phone",
    ConversationChannel.sms: "customer_phone",
    ConversationChannel.email: "customer_email",
}


class ReplyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


class ReplyResult(BaseModel):
    message_id: uuid.UUID
    delivery: str
    reason: Optional[str] = None


def get_reply_sender() -> ChannelOutboundSender:
    """The channel sender. Tests replace this dependency; production uses the configured channels."""
    return ChannelOutboundSender()


async def _deliver(
    sender: ChannelOutboundSender,
    conversation: Conversation,
    text: str,
    organization_id: uuid.UUID,
) -> tuple[str, Optional[str]]:
    channel = conversation.channel
    if channel == ConversationChannel.chat:
        return "delivered", None
    if channel == ConversationChannel.instagram:
        return "not_configured", "No Instagram address is stored for this conversation."
    field = _ADDRESS_FIELD.get(channel)
    if field is None:
        return (
            "not_configured",
            f"Replies cannot be sent on the {channel.value} channel.",
        )
    address = getattr(conversation, field)
    if not address:
        return "not_configured", "The customer has no address on this channel."
    try:
        await sender.send(
            channel=channel.value,
            recipient=address,
            text=text,
            organization_id=organization_id,
            lead_id=None,
        )
    except OutboundNotConfigured as exc:
        return "not_configured", str(exc)
    except Exception:  # noqa: BLE001 - provider detail stays in the log only
        log.warning(
            "inbox reply failed on %s for conversation %s",
            channel.value,
            conversation.id,
        )
        return (
            "failed",
            "The message could not be sent. Try again, or contact the customer directly.",
        )
    return "sent", None


@router.post(
    "/conversations/{conversation_id}/replies",
    response_model=ReplyResult,
    status_code=status.HTTP_201_CREATED,
)
async def reply_to_conversation(
    conversation_id: uuid.UUID,
    payload: ReplyRequest,
    ctx: OrgContext = Depends(require_permission(Permission.CHAT_USE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
    sender: ChannelOutboundSender = Depends(get_reply_sender),
) -> ReplyResult:
    conversation = await session.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.organization_id == pctx.organization_id)
        .where(Conversation.project_id == pctx.project_id)
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
        )

    text = payload.text.strip()
    now = datetime.now(timezone.utc)
    message = Message(
        conversation_id=conversation.id,
        sender=MessageSender.agent,
        message=text,
        metadata_={"human": True, "user_id": str(ctx.user_id), "delivery": "pending"},
    )
    session.add(message)
    await session.flush()

    delivery, reason = await _deliver(sender, conversation, text, pctx.organization_id)
    message.metadata_ = {
        **message.metadata_,
        "delivery": delivery,
        "delivery_reason": reason,
    }
    conversation.last_message_at = now
    if delivery in ("delivered", "sent"):
        # A real person has answered, so the open escalation (if any) records its first reply.
        await escalation_service.record_human_reply(session, conversation.id, at=now)
    await session.commit()
    return ReplyResult(message_id=message.id, delivery=delivery, reason=reason)

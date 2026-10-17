"""Outbound senders for the workflow ``send_message`` step.

A workflow send goes through the same channel adapters the inbox uses
(:mod:`app.services.channels.adapters`). The sender finds the organization's
enabled :class:`AgentChannel` for the lead's channel, checks that the provider
is configured, and calls the adapter's ``send``. It never reports success for a
message that was not delivered: a missing binding or missing credentials raise
:class:`OutboundNotConfigured` with a plain reason, and a provider refusal raises
a generic error.

Consent (``check_outbound``) is enforced by the workflow engine before any
sender is called, so this module does not repeat the policy.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Callable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent_channel import AgentChannel, ChannelStatus
from app.services.channels.adapters import ParsedInbound, get_adapter
from app.services.channels.config import ChannelsConfig, get_channels_config

log = logging.getLogger("app.workflow.senders")

# Channels a workflow send_message step can use.
SUPPORTED_CHANNELS: tuple[str, ...] = ("whatsapp", "sms", "instagram", "email")

# Provider adapters (by ``AgentChannel.provider``) that may carry each channel.
_PROVIDERS_BY_CHANNEL: dict[str, tuple[str, ...]] = {
    "whatsapp": ("twilio", "meta"),
    "sms": ("twilio",),
    "instagram": ("meta_instagram",),
    "email": ("email",),
}


class OutboundNotConfigured(Exception):
    """The channel cannot send right now. The message is safe to show to users."""


class ChannelOutboundSender:
    """Routes one workflow message to the organization's configured channel binding.

    ``session_factory`` returns an async session used only for the read of the
    binding. Tests inject a fake; production uses the app session maker.
    """

    def __init__(
        self,
        session_factory: Optional[Callable[[], Any]] = None,
        config_provider: Optional[Callable[[], ChannelsConfig]] = None,
    ) -> None:
        self._session_factory = session_factory or _default_session_factory
        self._config = config_provider or get_channels_config

    async def send(
        self,
        *,
        channel: str,
        recipient: str,
        text: str,
        organization_id: uuid.UUID,
        lead_id: uuid.UUID,
    ) -> dict[str, Any]:
        if channel not in SUPPORTED_CHANNELS:
            raise OutboundNotConfigured(
                f"Messages cannot be sent on the {channel} channel."
            )
        cfg = self._config()
        async with self._session_factory() as session:  # type: AsyncSession
            bindings = await find_bindings(session, organization_id, channel)

        if not bindings:
            raise OutboundNotConfigured(
                f"No enabled {channel} channel is set up for this organization, "
                "so the message was not sent."
            )

        reasons: list[str] = []
        for binding in bindings:
            reason = _not_ready_reason(cfg, channel, binding)
            if reason is None:
                return await _deliver(cfg, channel, binding, recipient, text)
            reasons.append(reason)
        raise OutboundNotConfigured(
            f"The {channel} channel is not configured, so the message was not sent. {reasons[0]}"
        )


async def find_bindings(
    session: AsyncSession, organization_id: uuid.UUID, channel: str
) -> list[AgentChannel]:
    """Enabled, active bindings for one organization and channel, oldest first."""
    stmt = (
        select(AgentChannel)
        .where(
            AgentChannel.organization_id == organization_id,
            AgentChannel.channel == channel,
            AgentChannel.enabled.is_(True),
            AgentChannel.status == ChannelStatus.active,
        )
        .order_by(AgentChannel.created_at, AgentChannel.id)
    )
    return list((await session.scalars(stmt)).all())


def _not_ready_reason(
    cfg: ChannelsConfig, channel: str, binding: AgentChannel
) -> Optional[str]:
    """None when the binding can send now; otherwise a plain reason with no secrets."""
    provider = (binding.provider or "").strip()
    if provider not in _PROVIDERS_BY_CHANNEL.get(channel, ()):
        return f"The {channel} binding has no supported provider set."
    adapter = get_adapter(provider)
    if adapter is None or channel not in adapter.channels:
        return f"The {channel} provider '{provider}' is not available on this server."

    extra = binding.configuration or {}
    if provider == "twilio":
        if not cfg.twilio_configured:
            return "Twilio is not configured on the server (account SID or auth token is missing)."
        if not (binding.phone_number or "").strip():
            return f"The {channel} binding has no phone number."
    elif provider == "meta":
        if not cfg.meta_whatsapp_access_token:
            return (
                "The WhatsApp Cloud API access token is not configured on the server."
            )
        if not str(extra.get("phone_number_id") or "").strip():
            return "The WhatsApp binding has no phone_number_id."
    elif provider == "meta_instagram":
        if not cfg.meta_instagram_access_token:
            return "The Instagram access token is not configured on the server."
        if not str(extra.get("instagram_account_id") or "").strip():
            return "The Instagram binding has no instagram_account_id."
    elif provider == "email":
        return "Email delivery is not connected on this server yet."
    return None


def build_parsed(
    *, channel: str, provider: str, binding: AgentChannel, recipient: str, text: str
) -> ParsedInbound:
    """Build the ParsedInbound context an adapter's ``send`` reads from the lead's fields."""
    extra = binding.configuration or {}
    address = recipient.strip()
    if provider == "twilio":
        from_number = (binding.phone_number or "").strip()
        # Twilio WhatsApp addresses carry the "whatsapp:" prefix on both ends.
        to_addr = address
        if channel == "whatsapp" and not address.startswith("whatsapp:"):
            to_addr = f"whatsapp:{address}"
        return ParsedInbound(
            channel=channel,
            provider=provider,
            text=text,
            to_address=from_number or None,
            phone=address,
            reply_to=to_addr,
        )
    if provider == "meta":
        digits = re.sub(r"\D", "", address)  # Cloud API takes digits without '+'
        return ParsedInbound(
            channel=channel,
            provider=provider,
            text=text,
            to_address=str(extra.get("phone_number_id") or "") or None,
            phone=digits,
            reply_to=digits,
        )
    if provider == "meta_instagram":
        return ParsedInbound(
            channel=channel,
            provider=provider,
            text=text,
            to_address=str(extra.get("instagram_account_id") or "") or None,
            external_id=address,
            reply_to=address,
        )
    return ParsedInbound(
        channel=channel,
        provider=provider,
        text=text,
        email=address.lower(),
        reply_to=address.lower(),
    )


async def _deliver(
    cfg: ChannelsConfig,
    channel: str,
    binding: AgentChannel,
    recipient: str,
    text: str,
) -> dict[str, Any]:
    provider = binding.provider or ""
    adapter = get_adapter(provider)
    if adapter is None:  # guarded by _not_ready_reason; kept for type safety
        raise OutboundNotConfigured(f"The {channel} provider is not available.")
    parsed = build_parsed(
        channel=channel,
        provider=provider,
        binding=binding,
        recipient=recipient,
        text=text,
    )
    try:
        accepted = await adapter.send(binding=binding, parsed=parsed, text=text)
    except Exception as exc:  # noqa: BLE001 - provider detail stays in the log only
        log.warning("%s adapter raised %s", provider, type(exc).__name__)
        raise RuntimeError(
            f"The {channel} provider did not accept the message."
        ) from exc
    if not accepted:
        # The adapter returns False for any non-2xx answer or transport error.
        raise RuntimeError(f"The {channel} provider did not accept the message.")
    return {"provider": provider, "binding_id": str(binding.id)}


def _default_session_factory():
    from app.database import session as db_session

    if db_session.AsyncSessionLocal is None:
        db_session.init_engine()
    return db_session.AsyncSessionLocal()

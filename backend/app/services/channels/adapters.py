"""Channel adapters (Phase M) — provider glue for the omnichannel pipeline.

Each adapter does two narrow jobs and **nothing else**:

* ``parse``  — normalise a provider webhook into a :class:`ParsedInbound`
  (who messaged, what they said, and how to route it to an agent), and
* ``send``   — deliver the agent's reply back over that provider's API.

The AI itself lives entirely in :mod:`app.services.omnichannel_service`
(identity + memory + RAG), so adapters never touch model logic. New channels
are added by writing one small adapter and registering it here.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from app.database.models.agent_channel import AgentChannel
from app.services.channels.config import get_channels_config

log = logging.getLogger("app.channels.adapters")

_HTTP_TIMEOUT = 15.0


@dataclass
class ParsedInbound:
    """Provider-agnostic view of one inbound message + routing hints."""

    channel: str                       # "whatsapp" | "sms" | "telegram" | …
    provider: str                      # "twilio" | "telegram" | "meta" | …
    text: str
    # Routing hints — used to find the AgentChannel binding.
    to_address: Optional[str] = None   # business number / page id / inbox
    bot_token: Optional[str] = None    # telegram bot token (path-based routing)
    route_value: Optional[str] = None  # generic value matched in configuration
    # Sender identity (whichever the channel knows).
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    handle: Optional[str] = None
    external_id: Optional[str] = None
    external_thread_id: Optional[str] = None
    reply_to: Optional[str] = None     # where to send the reply (chat id, number)
    meta: dict[str, Any] = field(default_factory=dict)


class ChannelAdapter:
    """Base adapter. Subclasses override ``parse`` and ``send``."""

    provider: str = ""
    channels: tuple[str, ...] = ()

    def parse(
        self,
        *,
        form: dict[str, Any],
        json: Optional[dict[str, Any]],
        headers: dict[str, str],
        params: dict[str, str],
    ) -> Optional[ParsedInbound]:
        raise NotImplementedError

    async def send(
        self, *, binding: AgentChannel, parsed: ParsedInbound, text: str
    ) -> bool:
        """Deliver ``text`` back to the user. Returns True on success."""
        return False


# ─────────────────────────────── Twilio (WhatsApp + SMS) ──────────────────────

class TwilioMessagingAdapter(ChannelAdapter):
    provider = "twilio"
    channels = ("whatsapp", "sms")

    @staticmethod
    def _strip(num: str) -> str:
        return (num or "").replace("whatsapp:", "").strip()

    def parse(self, *, form, json, headers, params):
        body = (form.get("Body") or "").strip()
        from_raw = form.get("From") or ""
        to_raw = form.get("To") or ""
        if not from_raw or not to_raw:
            return None
        is_whatsapp = from_raw.startswith("whatsapp:") or to_raw.startswith("whatsapp:")
        channel = "whatsapp" if is_whatsapp else "sms"
        from_num = self._strip(from_raw)
        to_num = self._strip(to_raw)
        return ParsedInbound(
            channel=channel,
            provider=self.provider,
            text=body,
            to_address=to_num,
            phone=from_num,
            name=(form.get("ProfileName") or None) if is_whatsapp else None,
            external_id=from_num,
            external_thread_id=form.get("MessageSid") or None,
            reply_to=from_raw,  # keep the whatsapp: prefix for the reply
            meta={"sms_message_sid": form.get("MessageSid")},
        )

    async def send(self, *, binding, parsed, text):
        cfg = get_channels_config()
        sid = cfg.twilio_account_sid
        token = cfg.twilio_auth_token
        if not (sid and token) or not text:
            log.info("twilio messaging not configured; reply not sent")
            return False
        from_addr = parsed.to_address or binding.phone_number or ""
        if parsed.channel == "whatsapp" and not from_addr.startswith("whatsapp:"):
            from_addr = f"whatsapp:{from_addr}"
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        data = {"From": from_addr, "To": parsed.reply_to or parsed.phone, "Body": text}
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.post(url, data=data, auth=(sid, token))
            if resp.status_code >= 400:
                log.warning("twilio send failed %s: %s", resp.status_code, resp.text[:200])
                return False
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("twilio send error: %s", e)
            return False


# ─────────────────────────────── Telegram ────────────────────────────────────

class TelegramAdapter(ChannelAdapter):
    provider = "telegram"
    channels = ("telegram",)

    def parse(self, *, form, json, headers, params):
        if not json:
            return None
        message = json.get("message") or json.get("edited_message") or {}
        text = (message.get("text") or "").strip()
        chat = message.get("chat") or {}
        sender = message.get("from") or {}
        chat_id = chat.get("id")
        if not text or chat_id is None:
            return None
        name = " ".join(
            p for p in [sender.get("first_name"), sender.get("last_name")] if p
        ) or sender.get("username")
        return ParsedInbound(
            channel="telegram",
            provider=self.provider,
            text=text,
            bot_token=params.get("token"),
            name=name,
            handle=sender.get("username"),
            external_id=str(sender.get("id")) if sender.get("id") is not None else None,
            external_thread_id=str(chat_id),
            reply_to=str(chat_id),
        )

    async def send(self, *, binding, parsed, text):
        token = (binding.configuration or {}).get("bot_token") or parsed.bot_token
        if not token or not text or parsed.reply_to is None:
            return False
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.post(
                    url, json={"chat_id": parsed.reply_to, "text": text}
                )
            return resp.status_code < 400
        except Exception as e:  # noqa: BLE001
            log.warning("telegram send error: %s", e)
            return False


# ─────────────────────────────── Email ───────────────────────────────────────

class EmailAdapter(ChannelAdapter):
    """Generic inbound-email webhook (SendGrid/SES/Mailgun-style JSON or form).

    Reply delivery requires SMTP/provider credentials; when absent, the answer
    is still persisted to the conversation and returned in the HTTP response so
    nothing is lost.
    """

    provider = "email"
    channels = ("email",)

    def parse(self, *, form, json, headers, params):
        data = json or form or {}
        sender = data.get("from") or data.get("sender") or ""
        to_addr = data.get("to") or data.get("recipient") or ""
        text = (data.get("text") or data.get("body-plain") or data.get("body") or "").strip()
        subject = data.get("subject") or ""
        if not sender or not text:
            return None
        return ParsedInbound(
            channel="email",
            provider=self.provider,
            text=(f"{subject}\n\n{text}".strip() if subject else text),
            to_address=str(to_addr).strip().lower() or None,
            email=str(sender).strip().lower(),
            external_id=str(sender).strip().lower(),
            external_thread_id=data.get("Message-Id") or data.get("message_id"),
            reply_to=str(sender).strip().lower(),
            meta={"subject": subject},
        )

    async def send(self, *, binding, parsed, text):
        # SMTP/provider delivery is configured per-deployment; persisted answer
        # is the source of truth. Treat as best-effort no-op when unconfigured.
        log.info("email reply ready (delivery via provider): to=%s", parsed.reply_to)
        return False


# ─────────────────────────────── SDK (mobile/desktop) ─────────────────────────

class SdkAdapter(ChannelAdapter):
    """Native mobile/desktop SDK — request carries identity inline and the
    reply is returned synchronously in the HTTP response (no async delivery)."""

    provider = "sdk"
    channels = ("mobile", "desktop")

    def parse(self, *, form, json, headers, params):
        data = json or {}
        text = (data.get("text") or data.get("message") or "").strip()
        if not text:
            return None
        user = data.get("user") or {}
        channel = (data.get("channel") or "mobile").strip()
        if channel not in self.channels:
            channel = "mobile"
        return ParsedInbound(
            channel=channel,
            provider=self.provider,
            text=text,
            route_value=str(data.get("agent_id") or "") or None,
            name=user.get("name"),
            email=user.get("email"),
            phone=user.get("phone"),
            external_id=user.get("id") or user.get("device_id"),
            external_thread_id=data.get("session_id"),
            meta={k: v for k, v in user.items() if k not in ("name", "email", "phone", "id")},
        )

    async def send(self, *, binding, parsed, text):
        return True  # delivered inline in the HTTP response


# ─────────────────────────────── registry ────────────────────────────────────

_ADAPTERS: dict[str, ChannelAdapter] = {}


def register(adapter: ChannelAdapter) -> None:
    _ADAPTERS[adapter.provider] = adapter


def get_adapter(provider: str) -> Optional[ChannelAdapter]:
    return _ADAPTERS.get(provider)


def supported_providers() -> list[str]:
    return sorted(_ADAPTERS.keys())


for _a in (TwilioMessagingAdapter(), TelegramAdapter(), EmailAdapter(), SdkAdapter()):
    register(_a)

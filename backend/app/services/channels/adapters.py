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

import hashlib
import hmac
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx
from twilio.request_validator import RequestValidator

from app.database.models.agent_channel import AgentChannel
from app.services.channels.config import get_channels_config

log = logging.getLogger("app.channels.adapters")

_HTTP_TIMEOUT = 15.0


@dataclass
class ParsedInbound:
    """Provider-agnostic view of one inbound message + routing hints."""

    channel: str  # "whatsapp" | "sms" | "telegram" | …
    provider: str  # "twilio" | "telegram" | "meta" | …
    text: str
    # Routing hints — used to find the AgentChannel binding.
    to_address: Optional[str] = None  # business number / page id / inbox
    bot_token: Optional[str] = None  # telegram bot token (path-based routing)
    route_value: Optional[str] = None  # generic value matched in configuration
    # Sender identity (whichever the channel knows).
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    handle: Optional[str] = None
    external_id: Optional[str] = None
    external_thread_id: Optional[str] = None
    reply_to: Optional[str] = None  # where to send the reply (chat id, number)
    # Provider's id for this message, namespaced by provider (e.g. "telegram:123").
    # Used to drop redelivered webhooks; None disables dedupe for that message.
    provider_message_id: Optional[str] = None
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
        sid = form.get("MessageSid") or None
        return ParsedInbound(
            channel=channel,
            provider=self.provider,
            text=body,
            to_address=to_num,
            phone=from_num,
            name=(form.get("ProfileName") or None) if is_whatsapp else None,
            external_id=from_num,
            external_thread_id=sid,
            reply_to=from_raw,  # keep the whatsapp: prefix for the reply
            provider_message_id=f"twilio:{sid}" if sid else None,
            meta={"sms_message_sid": sid},
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
                # Status only: the Twilio response body can echo phone numbers.
                log.warning("twilio send failed: HTTP %s", resp.status_code)
                return False
            return True
        except Exception as e:  # noqa: BLE001
            # Exception type only: transport errors can embed the request URL.
            log.warning("twilio send error: %s", type(e).__name__)
            return False


def verify_twilio_signature(
    auth_token: str, url: str, params: dict[str, Any], header: Optional[str]
) -> bool:
    """Check Twilio's ``X-Twilio-Signature``: HMAC-SHA1 of the URL plus sorted form fields.

    Fails closed on a missing token or header. ``url`` must be the public URL Twilio called.
    """
    if not auth_token or not header:
        return False
    return RequestValidator(auth_token).validate(url, params, header)


# ─────────────────────────────── Meta WhatsApp Cloud API ─────────────────────

_META_GRAPH_VERSION = "v21.0"


def _hmac_sha256_matches(secret: str, raw_body: bytes, header: Optional[str]) -> bool:
    """True when ``header`` is ``sha256=<hex HMAC-SHA256(secret, raw_body)>``. Fails closed."""
    if not secret or not header or not header.startswith("sha256="):
        return False
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={digest}", header)


def verify_meta_signature(
    app_secret: str, raw_body: bytes, header: Optional[str]
) -> bool:
    """Check Meta's ``X-Hub-Signature-256`` header against the raw request body.

    Fails closed: a missing secret or header means the request is rejected.
    """
    return _hmac_sha256_matches(app_secret, raw_body, header)


def verify_sdk_signature(
    secret: Optional[str], raw_body: bytes, header: Optional[str]
) -> bool:
    """Check an SDK request's ``X-OraOne-Signature`` against the binding's ``sdk_secret``.

    The secret lives in ``AgentChannel.configuration["sdk_secret"]``. A binding with no
    secret rejects every request (fail closed).
    """
    return _hmac_sha256_matches(secret or "", raw_body, header)


class MetaWhatsAppAdapter(ChannelAdapter):
    """WhatsApp via Meta's Cloud API (direct, no BSP). Text messages only for now."""

    provider = "meta"
    channels = ("whatsapp",)

    def parse(self, *, form, json, headers, params):
        if not json or json.get("object") != "whatsapp_business_account":
            return None
        for entry in json.get("entry") or []:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                messages = value.get("messages") or []
                if not messages:
                    # Status callbacks (delivered, read) arrive without messages.
                    continue
                message = messages[0]
                sender = message.get("from")
                text = ((message.get("text") or {}).get("body") or "").strip()
                if message.get("type") != "text" or not sender or not text:
                    return None
                contacts = value.get("contacts") or []
                profile = (contacts[0].get("profile") or {}) if contacts else {}
                phone_number_id = str(
                    (value.get("metadata") or {}).get("phone_number_id") or ""
                )
                wamid = message.get("id")
                return ParsedInbound(
                    channel="whatsapp",
                    provider=self.provider,
                    text=text,
                    to_address=phone_number_id or None,
                    name=profile.get("name"),
                    phone=sender,
                    external_id=sender,
                    external_thread_id=sender,
                    reply_to=sender,
                    provider_message_id=f"meta:{wamid}" if wamid else None,
                    meta={"message_id": wamid},
                )
        return None

    async def send(self, *, binding, parsed, text):
        cfg = get_channels_config()
        phone_number_id = (binding.configuration or {}).get(
            "phone_number_id"
        ) or parsed.to_address
        if (
            not cfg.meta_whatsapp_access_token
            or not phone_number_id
            or not text
            or not parsed.reply_to
        ):
            return False
        url = f"https://graph.facebook.com/{_META_GRAPH_VERSION}/{phone_number_id}/messages"
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {cfg.meta_whatsapp_access_token}"
                    },
                    json={
                        "messaging_product": "whatsapp",
                        "to": parsed.reply_to,
                        "type": "text",
                        "text": {"body": text},
                    },
                )
            if resp.status_code >= 300:
                # Log the status only; the response body can echo request details.
                log.warning("meta whatsapp send failed: HTTP %s", resp.status_code)
                return False
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("meta whatsapp send error: %s", type(e).__name__)
            return False


# ─────────────────────────────── Meta Instagram DMs ──────────────────────────


class MetaInstagramAdapter(ChannelAdapter):
    """Instagram direct messages via Meta's Messenger Platform. Text messages only."""

    provider = "meta_instagram"
    channels = ("instagram",)

    def parse(self, *, form, json, headers, params):
        if not json or json.get("object") != "instagram":
            return None
        for entry in json.get("entry") or []:
            for event in entry.get("messaging") or []:
                message = event.get("message") or {}
                # Read receipts, postbacks and echoes of our own replies carry no
                # inbound text from a customer, so they are skipped.
                if message.get("is_echo"):
                    continue
                text = (message.get("text") or "").strip()
                sender = ((event.get("sender") or {}).get("id") or "").strip()
                recipient = ((event.get("recipient") or {}).get("id") or "").strip()
                if not text or not sender or not recipient:
                    continue
                mid = message.get("mid")
                return ParsedInbound(
                    channel="instagram",
                    provider=self.provider,
                    text=text,
                    to_address=recipient,
                    external_id=sender,
                    external_thread_id=sender,
                    reply_to=sender,
                    provider_message_id=f"meta_instagram:{mid}" if mid else None,
                    meta={"message_id": mid},
                )
        return None

    async def send(self, *, binding, parsed, text):
        cfg = get_channels_config()
        if not cfg.meta_instagram_access_token or not text or not parsed.reply_to:
            return False
        url = f"https://graph.facebook.com/{_META_GRAPH_VERSION}/me/messages"
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {cfg.meta_instagram_access_token}"
                    },
                    json={
                        "recipient": {"id": parsed.reply_to},
                        "message": {"text": text},
                    },
                )
            if resp.status_code >= 300:
                # Log the status only; the response body can echo request details.
                log.warning("meta instagram send failed: HTTP %s", resp.status_code)
                return False
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("meta instagram send error: %s", type(e).__name__)
            return False


# ─────────────────────────────── Telegram ────────────────────────────────────


class TelegramAdapter(ChannelAdapter):
    provider = "telegram"
    channels = ("telegram",)

    def parse(self, *, form, json, headers, params):
        # The bot token is never read from the query string: the route supplies it from
        # the webhook path, and the header secret authenticates the request.
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
        update_id = json.get("update_id")
        return ParsedInbound(
            channel="telegram",
            provider=self.provider,
            text=text,
            bot_token=None,
            name=name,
            handle=sender.get("username"),
            external_id=str(sender.get("id")) if sender.get("id") is not None else None,
            external_thread_id=str(chat_id),
            reply_to=str(chat_id),
            provider_message_id=f"telegram:{update_id}"
            if update_id is not None
            else None,
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
            # Exception type only: the httpx error text embeds the URL, which holds the bot token.
            log.warning("telegram send error: %s", type(e).__name__)
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
        text = (
            data.get("text") or data.get("body-plain") or data.get("body") or ""
        ).strip()
        subject = data.get("subject") or ""
        if not sender or not text:
            return None
        # The From header is sender-asserted. It is used only to route the reply and to
        # key this email thread; it is not stored as a verified email identity, so it
        # cannot link this thread to another channel's visitor profile.
        sender_addr = str(sender).strip().lower()
        mid = data.get("Message-Id") or data.get("message_id")
        return ParsedInbound(
            channel="email",
            provider=self.provider,
            text=(f"{subject}\n\n{text}".strip() if subject else text),
            to_address=str(to_addr).strip().lower() or None,
            email=None,
            external_id=sender_addr,
            external_thread_id=mid,
            reply_to=sender_addr,
            provider_message_id=f"email:{str(mid).strip()}" if mid else None,
            meta={"subject": subject},
        )

    async def send(self, *, binding, parsed, text):
        # SMTP/provider delivery is configured per-deployment; persisted answer
        # is the source of truth. Treat as best-effort no-op when unconfigured.
        # No recipient address in logs: it is personal data.
        log.info("email reply ready (delivery via provider): channel=email")
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
            meta={
                k: v
                for k, v in user.items()
                if k not in ("name", "email", "phone", "id")
            },
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


for _a in (
    TwilioMessagingAdapter(),
    MetaWhatsAppAdapter(),
    MetaInstagramAdapter(),
    TelegramAdapter(),
    EmailAdapter(),
    SdkAdapter(),
):
    register(_a)

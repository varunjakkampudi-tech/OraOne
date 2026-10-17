"""Shared messaging-channel configuration (env-driven).

Twilio credentials are used by the omnichannel adapters (WhatsApp / SMS) to
send outbound replies. Optional at import time so the server still boots
without messaging credentials configured; adapters degrade gracefully.
"""

from __future__ import annotations

import os
from functools import lru_cache


def _get(*keys: str, default: str = "") -> str:
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v.strip()
    return default


class ChannelsConfig:
    """Lazily-read messaging channel settings. Built via :func:`get_channels_config`."""

    def __init__(self) -> None:
        self.twilio_account_sid = _get("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = _get("TWILIO_AUTH_TOKEN")
        self.twilio_phone_number = _get("TWILIO_PHONE_NUMBER")
        # Meta WhatsApp Cloud API (direct). The access token sends replies; the app
        # secret verifies webhook signatures; the verify token answers Meta's handshake.
        self.meta_whatsapp_access_token = _get("META_WHATSAPP_ACCESS_TOKEN")
        self.meta_whatsapp_app_secret = _get("META_WHATSAPP_APP_SECRET")
        self.meta_whatsapp_verify_token = _get("META_WHATSAPP_VERIFY_TOKEN")
        # Instagram DMs (Messenger Platform) use the same app secret and verify token as
        # WhatsApp; only the page/IG-scoped access token is separate.
        self.meta_instagram_access_token = _get("META_INSTAGRAM_ACCESS_TOKEN")
        # Shared secret the email provider sends in the X-Email-Inbound-Secret header.
        # Unset means every inbound email webhook is refused (fail closed).
        self.email_inbound_secret = _get("EMAIL_INBOUND_SECRET")
        # Public origin Twilio calls (e.g. https://api.example.com). Twilio signs this exact URL,
        # so behind a proxy it must be configured rather than inferred from the request.
        self.public_api_base_url = _get("PUBLIC_API_BASE_URL").rstrip("/")
        # Voice agent: optional E.164 team number for live handoff, and the Twilio <Say> voice.
        self.voice_handoff_number = _get("VOICE_HANDOFF_NUMBER")
        self.voice_say_voice = _get("VOICE_SAY_VOICE", default="alice")
        # Optional ElevenLabs text-to-speech for voice replies. Both the key and the voice
        # id must be set to use it; otherwise spoken replies use Twilio's built-in voice.
        self.elevenlabs_api_key = _get("ELEVENLABS_API_KEY")
        self.elevenlabs_voice_id = _get("ELEVENLABS_VOICE_ID")
        self.elevenlabs_model_id = _get(
            "ELEVENLABS_MODEL_ID", default="eleven_flash_v2_5"
        )

    @property
    def twilio_configured(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token)


@lru_cache(maxsize=1)
def get_channels_config() -> ChannelsConfig:
    return ChannelsConfig()

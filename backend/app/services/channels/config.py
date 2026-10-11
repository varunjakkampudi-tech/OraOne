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

    @property
    def twilio_configured(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token)


@lru_cache(maxsize=1)
def get_channels_config() -> ChannelsConfig:
    return ChannelsConfig()

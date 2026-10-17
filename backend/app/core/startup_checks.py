"""Fail-fast configuration checks for production-like deployments.

Runs once at application startup (called from the server lifespan). In
``production``, ``prod`` or ``staging`` it refuses to boot when an enabled
provider is missing a secret it cannot operate or verify webhooks without.
Local development is never blocked.

Error messages list only setting NAMES and the reason a setting is wrong.
Values are never included, so the output is safe to put in logs.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

PRODUCTION_LIKE_ENVIRONMENTS = frozenset({"production", "prod", "staging"})
MIN_JWT_SECRET_LENGTH = 32


class StartupConfigurationError(RuntimeError):
    """Raised when a production-like deployment is missing required settings."""


def _value(env: Mapping[str, str], name: str) -> str:
    return (env.get(name) or "").strip()


def is_production_like(env: Mapping[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return _value(source, "ENVIRONMENT").lower() in PRODUCTION_LIKE_ENVIRONMENTS


def find_configuration_problems(env: Mapping[str, str] | None = None) -> list[str]:
    """Return ``NAME (reason)`` entries for every missing or invalid setting.

    The rules apply regardless of environment; callers decide whether to
    enforce them (see :func:`validate_startup_configuration`).
    """
    source = os.environ if env is None else env
    problems: list[str] = []

    def add(entry: str) -> None:
        if entry not in problems:
            problems.append(entry)

    # Local access tokens are signed with this key; a short key is forgeable.
    if len(_value(source, "JWT_SECRET_KEY")) < MIN_JWT_SECRET_LENGTH:
        add("JWT_SECRET_KEY (missing or shorter than 32 characters)")

    # Twilio: any TWILIO_* setting being present means the integration is in use.
    twilio_in_use = any(
        name.startswith("TWILIO_") and _value(source, name) for name in source
    )
    if twilio_in_use:
        if not _value(source, "TWILIO_ACCOUNT_SID"):
            add("TWILIO_ACCOUNT_SID")
        if not _value(source, "TWILIO_AUTH_TOKEN"):
            add("TWILIO_AUTH_TOKEN")
        # Twilio signs the exact public URL, so it must be configured and https.
        public_base = _value(source, "PUBLIC_API_BASE_URL")
        if not public_base:
            add("PUBLIC_API_BASE_URL (required when Twilio is configured)")
        elif not public_base.lower().startswith("https://"):
            add(
                "PUBLIC_API_BASE_URL (must be an https:// URL when Twilio is configured)"
            )

    # Meta: webhook signatures for WhatsApp and Instagram share one app secret.
    if _value(source, "META_WHATSAPP_ACCESS_TOKEN") or _value(
        source, "META_INSTAGRAM_ACCESS_TOKEN"
    ):
        if not _value(source, "META_WHATSAPP_APP_SECRET"):
            add("META_WHATSAPP_APP_SECRET (required when a Meta access token is set)")

    # AI replies need a model provider key.
    if not _value(source, "OPENROUTER_API_KEY"):
        add("OPENROUTER_API_KEY (required for AI replies)")

    return problems


def validate_startup_configuration(env: Mapping[str, str] | None = None) -> None:
    """Raise :class:`StartupConfigurationError` in production-like environments.

    Does nothing in development, so local runs need no provider secrets.
    """
    source = os.environ if env is None else env
    if not is_production_like(source):
        return
    problems = find_configuration_problems(source)
    if problems:
        raise StartupConfigurationError(
            "Refusing to start: incomplete configuration for a production-like "
            "environment. Missing or invalid settings (values not shown): "
            + "; ".join(problems)
        )

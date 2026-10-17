"""Pseudonymous identifiers for log lines.

Logs should carry IDs, never personal data. Where an identifier is still needed
to correlate events (an email recipient, an auth subject), log a short SHA-256
fingerprint instead of the raw value.
"""

from __future__ import annotations

import hashlib


def fingerprint(value: object) -> str:
    """Stable, non-reversible label for ``value`` (``none`` when empty)."""
    if value is None or value == "":
        return "none"
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return f"sha256:{digest[:16]}"


def redact_email(address: str | None) -> str:
    """Fingerprint an email address (case-insensitive, whitespace-trimmed)."""
    if not address:
        return "none"
    return fingerprint(address.strip().lower())


def subject_fingerprint(subject: object) -> str:
    """Fingerprint an auth subject claim before it reaches a log line."""
    return fingerprint(subject)


def route_label(request: object) -> str:
    """The matched route template (for example ``/api/telegram/{token}/inbound``).

    Logging the raw path can leak secrets carried in it, such as bot tokens or share
    links. The template contains no values. Unmatched requests get a fixed label.
    """
    route = getattr(request, "scope", {}).get("route")
    template = getattr(route, "path", None)
    return template or "unmatched"

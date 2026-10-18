"""Pseudonymous identifiers and scrubbing for log lines and error records.

Logs should carry IDs, never personal data. Where an identifier is still needed
to correlate events (an email recipient, an auth subject, an organization), log a
short SHA-256 fingerprint instead of the raw value.

``scrub_text`` is a backstop for free text (exception messages, stack traces,
log excerpts). Callers still avoid putting personal data into messages; the
scrubber removes the common shapes if they slip through.
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit, urlunsplit


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


# ---------------------------------------------------------------------------
# Free-text scrubbing
# ---------------------------------------------------------------------------

REDACTED = "[redacted]"

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_URL_RE = re.compile(r"https?://[^\s\"'<>]+")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}")
_KNOWN_SECRET_RE = re.compile(
    r"\b(?:sk|pk|rk|whsec|xox[abprs]|ghp|gho|github_pat)[-_][A-Za-z0-9_-]{8,}"
    r"|\bAKIA[0-9A-Z]{16}\b"
)
_KEY_VALUE_RE = re.compile(
    r"(?i)\b(token|access_token|refresh_token|secret|password|passwd|api[_-]?key"
    r"|authorization|signature|code)\b(\s*[=:]\s*)[^\s,;&\"']+"
)
_LONG_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]{32,}")


def _strip_url(match: "re.Match[str]") -> str:
    parts = urlsplit(match.group(0))
    # Query strings and fragments carry share tokens, reset codes and signatures.
    stripped = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    return f"{stripped}?{REDACTED}" if parts.query else stripped


def _mask_long_token(match: "re.Match[str]") -> str:
    value = match.group(0)
    # Long identifiers made only of letters are code names, not credentials.
    if re.search(r"\d", value) and re.search(r"[A-Za-z]", value):
        return REDACTED
    return value


def scrub_text(value: object, *, limit: int | None = None) -> str:
    """Remove emails, credentials and URL query strings from free text."""
    text = "" if value is None else str(value)
    text = _URL_RE.sub(_strip_url, text)
    text = _EMAIL_RE.sub("[email]", text)
    text = _BEARER_RE.sub(f"Bearer {REDACTED}", text)
    text = _JWT_RE.sub(REDACTED, text)
    text = _KNOWN_SECRET_RE.sub(REDACTED, text)
    text = _KEY_VALUE_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)
    text = _LONG_TOKEN_RE.sub(_mask_long_token, text)
    if limit is not None and len(text) > limit:
        text = text[: max(0, limit - 3)] + "..."
    return text


def scrub_secrets(value: object) -> str:
    """Remove credential-shaped strings only, for text sent back to customers.

    Unlike ``scrub_text`` this keeps emails, URLs and ordinary words, because a
    business's own support address or help link is legitimate reply content.
    It removes bearer tokens, JWTs and well-known provider key prefixes that
    could appear in a knowledge-base passage and be echoed in a reply.
    """
    text = "" if value is None else str(value)
    text = _BEARER_RE.sub(f"Bearer {REDACTED}", text)
    text = _JWT_RE.sub(REDACTED, text)
    return _KNOWN_SECRET_RE.sub(REDACTED, text)


def replace_raw_path(text: str, raw_path: str | None, route_template_value: str) -> str:
    """Swap a concrete request path (which may hold a token) for its route template."""
    if raw_path and len(raw_path) >= 4 and raw_path != route_template_value:
        return text.replace(raw_path, route_template_value)
    return text


def format_frames(
    frames: list[tuple[str, int, str]], *, max_frames: int = 12
) -> list[str]:
    """Format the innermost ``max_frames`` frames as ``dir/file.py:line in func``.

    Only the last three path segments are kept, so a record does not reveal the
    deployment's directory layout, and source line text is never included.
    """
    lines: list[str] = []
    for filename, lineno, func_name in frames[-max_frames:]:
        short = "/".join(re.split(r"[\\/]", filename)[-3:])
        lines.append(f"{short}:{lineno} in {func_name}")
    return lines

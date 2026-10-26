"""Send transactional email through Resend's HTTPS API.

Used for one-time sign-in codes. The API key is read by the caller from server
configuration and is never logged, returned or placed in a URL. Provider
response bodies are not logged either, because they can echo recipient data.

Retries are bounded and reuse the same ``Idempotency-Key``, so a retry after a
timeout cannot send the same code twice to the same recipient.
"""

from __future__ import annotations

import logging
import os
import time

import httpx

log = logging.getLogger("app.email.resend")

RESEND_EMAILS_URL = "https://api.resend.com/emails"
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = (0.5, 1.5)
_TIMEOUT_SECONDS = 10.0


class LiveEmailBlockedError(RuntimeError):
    """A test tried to reach the live mail provider without an explicit opt-in."""


def _check_live_send_allowed(to: str, transport) -> None:
    """Refuse live sends from automated tests unless explicitly allowed.

    A developer machine can hold a real key. Inside pytest, a live call is allowed only
    with ``ORAONE_LIVE_EMAIL_TEST=1`` and a recipient listed in
    ``ORAONE_LIVE_EMAIL_RECIPIENTS`` (comma-separated). Mock transports are always allowed.
    Outside pytest (the running application), this guard does nothing.
    """
    if transport is not None or "PYTEST_CURRENT_TEST" not in os.environ:
        return
    allowlist = {
        item.strip().lower()
        for item in os.environ.get("ORAONE_LIVE_EMAIL_RECIPIENTS", "").split(",")
        if item.strip()
    }
    opted_in = os.environ.get("ORAONE_LIVE_EMAIL_TEST") == "1"
    if not (opted_in and to.strip().lower() in allowlist):
        raise LiveEmailBlockedError(
            "live email is blocked in automated tests; see the live-test runbook"
        )


def send(
    *,
    api_key: str,
    from_address: str,
    to: str,
    subject: str,
    html: str,
    text: str,
    idempotency_key: str,
    transport: httpx.BaseTransport | None = None,
) -> bool:
    """Send one message. Returns True when Resend accepted it (2xx), else False."""
    _check_live_send_allowed(to, transport)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Idempotency-Key": idempotency_key,
        "Content-Type": "application/json",
    }
    payload = {
        "from": from_address,
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            with httpx.Client(transport=transport, timeout=_TIMEOUT_SECONDS) as client:
                response = client.post(RESEND_EMAILS_URL, headers=headers, json=payload)
        except httpx.TransportError as exc:
            log.warning(
                "resend_transport_error attempt=%d error=%s",
                attempt,
                type(exc).__name__,
            )
        else:
            if 200 <= response.status_code < 300:
                return True
            if response.status_code == 429 or response.status_code >= 500:
                log.warning(
                    "resend_retryable_status attempt=%d status=%d",
                    attempt,
                    response.status_code,
                )
            else:
                # 4xx means the request itself is wrong (bad key, bad sender); retrying cannot help.
                log.error("resend_rejected status=%d", response.status_code)
                return False
        if attempt < _MAX_ATTEMPTS:
            time.sleep(_BACKOFF_SECONDS[attempt - 1])
    log.error("resend_gave_up attempts=%d", _MAX_ATTEMPTS)
    return False

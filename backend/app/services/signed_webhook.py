"""Signed outbound JSON events (generic webhook sender).

Wire format, which receivers verify the same way:

    X-OraOne-Event:     <event type>
    X-OraOne-Delivery:  <delivery id, unique per event>
    X-OraOne-Timestamp: <unix seconds when the request was signed>
    X-OraOne-Signature: sha256=<hex HMAC-SHA256>

The signature covers ``"<timestamp>.<delivery id>.<raw body>"`` keyed by the
endpoint secret. Including the timestamp and delivery id in the signed string
stops a captured request from being replayed with a fresh timestamp or moved
to a different delivery. Receivers reject timestamps outside
``REPLAY_WINDOW_SECONDS`` and should remember delivery ids they have processed.

Delivery makes exactly one POST. There are no retries, and a retry would have
to reuse the same delivery id. The outcome is returned to the caller and logged
without the secret or the body.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlsplit

import httpx

from app.schemas.webhooks import validate_public_webhook_url

log = logging.getLogger("app.signed_webhook")

SIGNATURE_PREFIX = "sha256="
REPLAY_WINDOW_SECONDS = 300
_MIN_SECRET_LENGTH = 24
_TIMEOUT_SECONDS = 10.0


class SignedWebhookError(ValueError):
    """The destination or inputs are refused before any request is sent."""


class SignatureRejected(SignedWebhookError):
    """A received request failed verification. ``reason`` is a stable code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class DeliveryOutcome:
    delivery_id: str
    event: str
    host: str
    timestamp: int
    delivered: bool
    status_code: Optional[int]
    error: Optional[str]


def _require_secret(secret: str) -> None:
    if not secret or len(secret) < _MIN_SECRET_LENGTH:
        raise SignedWebhookError("signing secret is missing or too short.")


def _signed_material(timestamp: int, delivery_id: str, body: bytes) -> bytes:
    return f"{timestamp}.{delivery_id}.".encode("utf-8") + body


def sign(secret: str, *, timestamp: int, delivery_id: str, body: bytes) -> str:
    """Return the ``X-OraOne-Signature`` value for one request."""
    _require_secret(secret)
    digest = hmac.new(
        secret.encode("utf-8"),
        _signed_material(timestamp, delivery_id, body),
        hashlib.sha256,
    ).hexdigest()
    return f"{SIGNATURE_PREFIX}{digest}"


def verify(
    *,
    secret: str,
    body: bytes,
    delivery_id: str,
    timestamp_header: str,
    signature_header: str,
    now: Optional[int] = None,
    window_seconds: int = REPLAY_WINDOW_SECONDS,
) -> None:
    """Raise :class:`SignatureRejected` unless the request is authentic and fresh."""
    if not timestamp_header or not signature_header or not delivery_id:
        raise SignatureRejected("missing_headers")
    try:
        timestamp = int(timestamp_header)
    except ValueError:
        raise SignatureRejected("bad_timestamp") from None
    current = int(time.time()) if now is None else now
    if abs(current - timestamp) > window_seconds:
        raise SignatureRejected("stale_timestamp")
    expected = sign(secret, timestamp=timestamp, delivery_id=delivery_id, body=body)
    if not hmac.compare_digest(expected, signature_header):
        raise SignatureRejected("bad_signature")


def _assert_https_public(url: str) -> str:
    """Refuse non-HTTPS URLs and any host that is not public (loopback, private, reserved).

    Reuses the webhook URL validator from ``app.schemas.webhooks``, the same
    check the workflow engine and webhook endpoints rely on. It is repeated
    immediately before each request to narrow the DNS-rebinding window.
    """
    if urlsplit(url).scheme != "https":
        raise SignedWebhookError("webhook url must use https.")
    try:
        validate_public_webhook_url(url)
    except ValueError as exc:
        raise SignedWebhookError(str(exc)) from None
    return urlsplit(url).hostname or ""


async def send_event(
    url: str,
    *,
    event: str,
    data: dict[str, Any],
    secret: str,
    delivery_id: Optional[str] = None,
    now: Optional[int] = None,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> DeliveryOutcome:
    """Send one signed event with a single POST and return what happened.

    Raises :class:`SignedWebhookError` before any request if the URL or secret is
    refused. A transport failure or non-2xx response is returned as an outcome.
    """
    _require_secret(secret)
    host = await asyncio.to_thread(_assert_https_public, url)

    delivery = delivery_id or f"dlv_{uuid.uuid4().hex}"
    timestamp = int(time.time()) if now is None else now
    body = json.dumps(
        {"id": delivery, "type": event, "created": timestamp, "data": data},
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "OraOne-Signed-Webhooks/1.0",
        "X-OraOne-Event": event,
        "X-OraOne-Delivery": delivery,
        "X-OraOne-Timestamp": str(timestamp),
        "X-OraOne-Signature": sign(
            secret, timestamp=timestamp, delivery_id=delivery, body=body
        ),
    }

    status_code: Optional[int] = None
    error: Optional[str] = None
    delivered = False
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT_SECONDS, follow_redirects=False, transport=transport
        ) as client:
            response = await client.post(url, content=body, headers=headers)
        status_code = response.status_code
        delivered = 200 <= status_code < 300
        if not delivered:
            error = f"HTTP {status_code}"
    except httpx.HTTPError as exc:
        error = type(exc).__name__

    outcome = DeliveryOutcome(
        delivery_id=delivery,
        event=event,
        host=host,
        timestamp=timestamp,
        delivered=delivered,
        status_code=status_code,
        error=error,
    )
    log.info(
        "signed webhook delivery=%s event=%s host=%s delivered=%s status=%s",
        outcome.delivery_id,
        outcome.event,
        outcome.host,
        outcome.delivered,
        outcome.status_code,
    )
    return outcome

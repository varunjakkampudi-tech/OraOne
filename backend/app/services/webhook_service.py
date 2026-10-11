"""Webhook delivery service (R7).

Org-scoped outbound webhooks. Endpoints subscribe to a set of event types and
receive signed JSON ``POST`` requests when those events fire. Deliveries are
signed with an HMAC-SHA256 signature derived from the endpoint's ``secret`` so
receivers can verify authenticity (Stripe-style ``t=<ts>,v1=<sig>`` header).

Dispatch is best-effort and fire-and-forget: a single delivery is attempted
(with a couple of fast retries) in a background task so request latency on the
triggering action is never affected. Every attempt is recorded as a
``WebhookDelivery`` row for the developer dashboard.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.webhook import (
    WebhookDelivery,
    WebhookEndpoint,
    WebhookEventType,
    WebhookStatus,
)
from app.database.session import session_scope

logger = logging.getLogger("oraone.webhooks")

_MAX_ATTEMPTS = 3
_RETRY_BACKOFF = (0.0, 1.5, 4.0)  # seconds before each attempt
_TIMEOUT = 10.0
_AUTO_DISABLE_AFTER = 15  # consecutive failures before auto-disable


# ── helpers ─────────────────────────────────────────────────────────────────
def generate_secret() -> str:
    """A signing secret shown once when an endpoint is created/rotated."""
    return "whsec_" + secrets.token_urlsafe(32)[:48]


def sign_payload(secret: str, body: bytes, timestamp: Optional[int] = None) -> tuple[int, str]:
    """Return ``(timestamp, signature)`` for the given raw body."""
    ts = timestamp or int(time.time())
    signed = f"{ts}.".encode("utf-8") + body
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return ts, digest


def signature_header(secret: str, body: bytes) -> str:
    ts, sig = sign_payload(secret, body)
    return f"t={ts},v1={sig}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def event_catalogue() -> list[dict[str, str]]:
    labels = {
        WebhookEventType.CONVERSATION_CREATED: "A new conversation started",
        WebhookEventType.CONVERSATION_FINISHED: "A conversation was closed/resolved",
        WebhookEventType.MESSAGE_CREATED: "A new message was added to a conversation",
        WebhookEventType.DOCUMENT_UPLOADED: "A document was uploaded",
        WebhookEventType.DOCUMENT_PROCESSED: "A document finished processing/embedding",
        WebhookEventType.WEBSITE_CRAWLED: "A website crawl completed",
        WebhookEventType.WORKFLOW_FINISHED: "A workflow run finished",
        WebhookEventType.INTEGRATION_SYNCED: "An integration completed a sync",
        WebhookEventType.LEAD_GENERATED: "A lead was captured (widget/chat)",
        WebhookEventType.WIDGET_INSTALLED: "A widget was published/installed",
        WebhookEventType.WIDGET_ESCALATION: "A widget conversation was escalated to a human",
    }
    return [{"event": e, "description": labels.get(e, e)} for e in WebhookEventType.ALL]


# ── CRUD ────────────────────────────────────────────────────────────────────
async def list_endpoints(
    session: AsyncSession,
    organization_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
) -> list[WebhookEndpoint]:
    stmt = (
        select(WebhookEndpoint)
        .where(
            WebhookEndpoint.organization_id == organization_id,
            WebhookEndpoint.deleted_at.is_(None),
        )
        .order_by(WebhookEndpoint.created_at.desc())
    )
    if project_id is not None:
        stmt = stmt.where(WebhookEndpoint.project_id == project_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_endpoint(
    session: AsyncSession, organization_id: uuid.UUID, endpoint_id: uuid.UUID
) -> Optional[WebhookEndpoint]:
    result = await session.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.organization_id == organization_id,
            WebhookEndpoint.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


def _normalize_events(events: Optional[Iterable[str]]) -> list[str]:
    if not events:
        return []
    valid = set(WebhookEventType.ALL)
    return [e for e in dict.fromkeys(events) if e in valid]


async def create_endpoint(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    url: str,
    events: Optional[Iterable[str]] = None,
    description: Optional[str] = None,
    created_by_user_id: Optional[uuid.UUID] = None,
    project_id: Optional[uuid.UUID] = None,
) -> WebhookEndpoint:
    endpoint = WebhookEndpoint(
        organization_id=organization_id,
        project_id=project_id,
        url=url.strip(),
        description=(description or None),
        secret=generate_secret(),
        status=WebhookStatus.ACTIVE,
        events=_normalize_events(events),
        created_by_user_id=created_by_user_id,
    )
    session.add(endpoint)
    await session.flush()
    return endpoint


async def update_endpoint(
    session: AsyncSession,
    endpoint: WebhookEndpoint,
    *,
    url: Optional[str] = None,
    events: Optional[Iterable[str]] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
) -> WebhookEndpoint:
    if url is not None:
        endpoint.url = url.strip()
    if events is not None:
        endpoint.events = _normalize_events(events)
    if description is not None:
        endpoint.description = description or None
    if status is not None and status in WebhookStatus.ALL:
        endpoint.status = status
        if status == WebhookStatus.ACTIVE:
            endpoint.failure_count = 0
    await session.flush()
    return endpoint


async def rotate_secret(session: AsyncSession, endpoint: WebhookEndpoint) -> WebhookEndpoint:
    endpoint.secret = generate_secret()
    await session.flush()
    return endpoint


async def delete_endpoint(session: AsyncSession, endpoint: WebhookEndpoint) -> None:
    endpoint.deleted_at = _now()
    await session.flush()


async def list_deliveries(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    endpoint_id: Optional[uuid.UUID] = None,
    limit: int = 50,
) -> list[WebhookDelivery]:
    stmt = select(WebhookDelivery).where(WebhookDelivery.organization_id == organization_id)
    if endpoint_id is not None:
        stmt = stmt.where(WebhookDelivery.endpoint_id == endpoint_id)
    stmt = stmt.order_by(WebhookDelivery.created_at.desc()).limit(min(limit, 200))
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ── delivery ────────────────────────────────────────────────────────────────
async def _deliver_once(endpoint: WebhookEndpoint, body: bytes, event: str) -> tuple[bool, Optional[int], Optional[str]]:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "OraOne-Webhooks/1.0",
        "X-OraOne-Event": event,
        "X-OraOne-Signature": signature_header(endpoint.secret, body),
        "X-OraOne-Delivery": str(uuid.uuid4()),
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(endpoint.url, content=body, headers=headers)
        ok = 200 <= resp.status_code < 300
        return ok, resp.status_code, None if ok else f"HTTP {resp.status_code}"
    except Exception as exc:  # noqa: BLE001 - report any transport error
        return False, None, str(exc)[:500]


async def _record_and_attempt(endpoint_id: uuid.UUID, organization_id: uuid.UUID, event: str, payload: dict[str, Any]) -> None:
    """Run in a background task with its own DB session."""
    body = json.dumps(payload, default=str, separators=(",", ":")).encode("utf-8")
    success = False
    status_code: Optional[int] = None
    error: Optional[str] = None
    attempts = 0

    try:
        async with session_scope() as session:
            endpoint = await session.get(WebhookEndpoint, endpoint_id)
            if endpoint is None or endpoint.deleted_at is not None:
                return
            if endpoint.status != WebhookStatus.ACTIVE:
                return

            for idx in range(_MAX_ATTEMPTS):
                if _RETRY_BACKOFF[idx]:
                    await asyncio.sleep(_RETRY_BACKOFF[idx])
                attempts = idx + 1
                success, status_code, error = await _deliver_once(endpoint, body, event)
                if success:
                    break

            delivery = WebhookDelivery(
                endpoint_id=endpoint.id,
                organization_id=organization_id,
                event=event,
                success=success,
                status_code=status_code,
                attempts=attempts,
                error=error,
                payload=payload,
            )
            session.add(delivery)

            endpoint.last_delivery_at = _now()
            endpoint.last_status = "success" if success else (error or "failed")[:40]
            if success:
                endpoint.failure_count = 0
            else:
                endpoint.failure_count = (endpoint.failure_count or 0) + 1
                if endpoint.failure_count >= _AUTO_DISABLE_AFTER:
                    endpoint.status = WebhookStatus.DISABLED
    except Exception:  # noqa: BLE001
        logger.exception("webhook delivery failed for endpoint=%s event=%s", endpoint_id, event)


def _envelope(event: str, organization_id: uuid.UUID, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": event,
        "created": int(time.time()),
        "organization_id": str(organization_id),
        "data": data,
    }


async def dispatch(organization_id: uuid.UUID, event: str, data: dict[str, Any]) -> int:
    """Fan out ``event`` to all active subscribed endpoints. Returns # scheduled.

    Non-blocking: each delivery runs in its own background task. Safe to call
    from request handlers; never raises.
    """
    try:
        async with session_scope() as session:
            result = await session.execute(
                select(WebhookEndpoint).where(
                    WebhookEndpoint.organization_id == organization_id,
                    WebhookEndpoint.status == WebhookStatus.ACTIVE,
                    WebhookEndpoint.deleted_at.is_(None),
                )
            )
            endpoints = list(result.scalars().all())
    except Exception:  # noqa: BLE001
        logger.exception("webhook dispatch lookup failed org=%s event=%s", organization_id, event)
        return 0

    payload = _envelope(event, organization_id, data)
    scheduled = 0
    for ep in endpoints:
        subscribed = (not ep.events) or (event in ep.events)
        if not subscribed:
            continue
        asyncio.create_task(_record_and_attempt(ep.id, organization_id, event, payload))
        scheduled += 1
    return scheduled


async def send_test(session: AsyncSession, endpoint: WebhookEndpoint) -> WebhookDelivery:
    """Synchronous single-shot test delivery used by the dashboard 'Send test'."""
    payload = _envelope("ping.test", endpoint.organization_id, {"message": "OraOne webhook test event"})
    body = json.dumps(payload, default=str, separators=(",", ":")).encode("utf-8")
    success, status_code, error = await _deliver_once(endpoint, body, "ping.test")
    delivery = WebhookDelivery(
        endpoint_id=endpoint.id,
        organization_id=endpoint.organization_id,
        event="ping.test",
        success=success,
        status_code=status_code,
        attempts=1,
        error=error,
        payload=payload,
    )
    session.add(delivery)
    endpoint.last_delivery_at = _now()
    endpoint.last_status = "success" if success else (error or "failed")[:40]
    await session.flush()
    return delivery

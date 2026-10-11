"""Webhook delivery service (R7).

Org-scoped outbound webhooks. Endpoints subscribe to a set of event types and
receive signed JSON ``POST`` requests when those events fire. Deliveries are
signed with an HMAC-SHA256 signature derived from the endpoint's ``secret`` so
receivers can verify authenticity (Stripe-style ``t=<ts>,v1=<sig>`` header).

Delivery is durable: business events are written to ``WebhookOutbox`` in the
same transaction as the triggering change, then the outbox worker performs
delivery and records every result in ``WebhookDelivery``. The compatibility
``dispatch`` entry point remains synchronous and never launches an untracked
background task.
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
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.webhook import (
    WebhookDelivery,
    WebhookEndpoint,
    WebhookEventType,
    WebhookStatus,
)
from app.schemas.webhooks import validate_public_webhook_url
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


def sign_payload(
    secret: str, body: bytes, timestamp: Optional[int] = None
) -> tuple[int, str]:
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


async def rotate_secret(
    session: AsyncSession, endpoint: WebhookEndpoint
) -> WebhookEndpoint:
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
    stmt = select(WebhookDelivery).where(
        WebhookDelivery.organization_id == organization_id
    )
    if endpoint_id is not None:
        stmt = stmt.where(WebhookDelivery.endpoint_id == endpoint_id)
    stmt = stmt.order_by(WebhookDelivery.created_at.desc()).limit(min(limit, 200))
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ── delivery ────────────────────────────────────────────────────────────────
async def _deliver_once(
    endpoint: WebhookEndpoint,
    body: bytes,
    event: str,
    *,
    delivery_id: str | None = None,
) -> tuple[bool, Optional[int], Optional[str]]:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "OraOne-Webhooks/1.0",
        "X-OraOne-Event": event,
        "X-OraOne-Signature": signature_header(endpoint.secret, body),
        "X-OraOne-Delivery": delivery_id or str(uuid.uuid4()),
    }
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT, follow_redirects=False
        ) as client:
            # Re-resolve and reject unsafe destinations immediately before the
            # request. Registration-time validation alone is vulnerable to DNS
            # rebinding. Redirects are deliberately disabled so each hop must
            # be explicitly registered and validated.
            validate_public_webhook_url(endpoint.url)
            resp = await client.post(endpoint.url, content=body, headers=headers)
        ok = 200 <= resp.status_code < 300
        return ok, resp.status_code, None if ok else f"HTTP {resp.status_code}"
    except Exception as exc:  # noqa: BLE001 - report any transport error
        return False, None, str(exc)[:500]


async def _deliver_endpoint(
    session: AsyncSession,
    endpoint: WebhookEndpoint,
    organization_id: uuid.UUID,
    event: str,
    payload: dict[str, Any],
) -> bool:
    """Deliver one endpoint and persist its result in the caller's session."""
    body = json.dumps(payload, default=str, separators=(",", ":")).encode("utf-8")
    success = False
    status_code: Optional[int] = None
    error: Optional[str] = None
    attempts = 0

    if endpoint.deleted_at is not None or endpoint.status != WebhookStatus.ACTIVE:
        return False

    for idx in range(_MAX_ATTEMPTS):
        if _RETRY_BACKOFF[idx]:
            await asyncio.sleep(_RETRY_BACKOFF[idx])
        attempts = idx + 1
        success, status_code, error = await _deliver_once(
            endpoint, body, event, delivery_id=payload.get("id")
        )
        if success:
            break

    session.add(
        WebhookDelivery(
            endpoint_id=endpoint.id,
            organization_id=organization_id,
            event=event,
            success=success,
            status_code=status_code,
            attempts=attempts,
            error=error,
            payload=payload,
        )
    )
    endpoint.last_delivery_at = _now()
    endpoint.last_status = "success" if success else (error or "failed")[:40]
    if success:
        endpoint.failure_count = 0
    else:
        endpoint.failure_count = (endpoint.failure_count or 0) + 1
        if endpoint.failure_count >= _AUTO_DISABLE_AFTER:
            endpoint.status = WebhookStatus.DISABLED
    return success


def _envelope(
    event: str,
    organization_id: uuid.UUID,
    data: dict[str, Any],
    *,
    event_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": event_id or f"evt_{uuid.uuid4().hex}",
        "type": event,
        "created": int(time.time()),
        "organization_id": str(organization_id),
        "data": data,
    }


@dataclass(frozen=True)
class DeliveryResult:
    attempted: int = 0
    succeeded: int = 0
    failed: int = 0


async def deliver_event(
    session: AsyncSession,
    organization_id: uuid.UUID,
    event: str,
    data: dict[str, Any],
    *,
    event_id: str | None = None,
    isolated_delivery: bool = False,
) -> DeliveryResult:
    """Deliver an event and report endpoint-level success/failure.

    ``isolated_delivery`` is used by the outbox worker: it commits the endpoint
    query before network I/O and commits each delivery record independently,
    so one slow or failing destination does not hold a business transaction.
    """
    result = await session.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.organization_id == organization_id,
            WebhookEndpoint.status == WebhookStatus.ACTIVE,
            WebhookEndpoint.deleted_at.is_(None),
        )
    )
    if isolated_delivery:
        await session.commit()
    payload = _envelope(event, organization_id, data, event_id=event_id)
    attempted = 0
    succeeded = 0
    failed = 0
    for endpoint in result.scalars().all():
        if (not endpoint.events) or (event in endpoint.events):
            already_succeeded = await session.scalar(
                select(WebhookDelivery.id)
                .where(
                    WebhookDelivery.endpoint_id == endpoint.id,
                    WebhookDelivery.event == event,
                    WebhookDelivery.success.is_(True),
                    WebhookDelivery.payload["id"].as_string() == payload["id"],
                )
                .limit(1)
            )
            if already_succeeded is not None:
                continue
            attempted += 1
            if await _deliver_endpoint(
                session, endpoint, organization_id, event, payload
            ):
                succeeded += 1
            else:
                failed += 1
            if isolated_delivery:
                await session.commit()
    return DeliveryResult(attempted=attempted, succeeded=succeeded, failed=failed)


async def dispatch(
    organization_id: uuid.UUID,
    event: str,
    data: dict[str, Any],
    *,
    event_id: str | None = None,
) -> int:
    """Compatibility wrapper that delivers without an untracked task."""
    try:
        async with session_scope() as session:
            result = await deliver_event(
                session, organization_id, event, data, event_id=event_id
            )
            return result.succeeded
    except Exception:  # noqa: BLE001
        logger.exception(
            "webhook dispatch failed org=%s event=%s", organization_id, event
        )
        return 0


async def send_test(
    session: AsyncSession, endpoint: WebhookEndpoint
) -> WebhookDelivery:
    """Synchronous single-shot test delivery used by the dashboard 'Send test'."""
    payload = _envelope(
        "ping.test", endpoint.organization_id, {"message": "OraOne webhook test event"}
    )
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

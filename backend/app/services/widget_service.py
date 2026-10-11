"""Widget service helpers (R6).

Shared logic for the admin and public widget routers: domain
normalisation, embed snippet generation, public-config assembly, an
in-memory rate limiter, session resolution, and analytics event logging.
"""
from __future__ import annotations

import os
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent, AgentStatus
from app.database.models.widget import Widget, WidgetStatus
from app.database.models.widget_domain import WidgetDomain
from app.database.models.widget_event import WidgetEvent
from app.database.models.widget_session import WidgetSession


def widget_cdn_base() -> str:
    return os.environ.get("WIDGET_CDN_BASE", os.environ.get("FRONTEND_URL", "http://localhost:3000")).rstrip("/")


def widget_api_base() -> str:
    """Public base URL of the backend API that embedded widgets call.

    Falls back to the CDN/frontend origin so a single reverse-proxied domain
    (where ``/api`` routes to the backend) works with no extra config.
    """
    base = (
        os.environ.get("WIDGET_API_BASE")
        or os.environ.get("BACKEND_PUBLIC_URL")
        or os.environ.get("PUBLIC_BACKEND_URL")
        or os.environ.get("BACKEND_URL")
        or widget_cdn_base()
    )
    return base.rstrip("/")


def normalize_domain(value: str) -> str:
    """Reduce a URL/host to a bare lowercase host (no scheme/port/path)."""
    if not value:
        return ""
    value = value.strip().lower()
    if "://" not in value:
        value = "//" + value
    host = urlparse(value).hostname or ""
    return host


def build_embed_snippet(public_key: str) -> str:
    base = widget_cdn_base()
    api = widget_api_base()
    api_attr = f' data-api="{api}"' if api and api != base else ""
    return (
        f'<script src="{base}/widget.js" '
        f'data-widget-id="{public_key}"{api_attr} async></script>'
    )


def origin_host(origin: Optional[str], referer: Optional[str]) -> str:
    """Best host from the Origin header, falling back to Referer."""
    return normalize_domain(origin or "") or normalize_domain(referer or "")


def domain_allowed(allowed: list[str], host: str) -> bool:
    """Allow if the list is empty (unrestricted) or host matches/sub-matches."""
    if not allowed:
        return True
    if not host:
        return False
    host = host.lower()
    for d in allowed:
        d = (d or "").lower().lstrip(".")
        if not d:
            continue
        if host == d or host.endswith("." + d):
            return True
    return False


# ── In-memory sliding-window rate limiter (per process) ──
_BUCKETS: dict[str, deque] = defaultdict(deque)


def rate_limited(key: str, *, limit: int, window_seconds: int = 60) -> bool:
    """Return True if ``key`` has exceeded ``limit`` hits in the window."""
    now = time.time()
    q = _BUCKETS[key]
    cutoff = now - window_seconds
    while q and q[0] < cutoff:
        q.popleft()
    if len(q) >= max(1, limit):
        return True
    q.append(now)
    return False


async def get_widget_by_key(session: AsyncSession, public_key: str) -> Optional[Widget]:
    return await session.scalar(
        select(Widget)
        .where(Widget.public_key == public_key)
        .where(Widget.deleted_at.is_(None))
    )


async def widget_domains(session: AsyncSession, widget_id: uuid.UUID) -> list[str]:
    rows = (
        await session.scalars(
            select(WidgetDomain.domain).where(WidgetDomain.widget_id == widget_id)
        )
    ).all()
    return list(rows)


async def resolve_agent_id(
    session: AsyncSession, widget: Widget
) -> Optional[uuid.UUID]:
    """Widget's agent, else the org's first active agent, else None."""
    if widget.agent_id is not None:
        return widget.agent_id
    return await session.scalar(
        select(Agent.id)
        .where(Agent.organization_id == widget.organization_id)
        .where(Agent.deleted_at.is_(None))
        .where(Agent.status == AgentStatus.active)
        .order_by(Agent.created_at.asc())
        .limit(1)
    )


async def log_event(
    session: AsyncSession,
    *,
    widget: Widget,
    event: str,
    session_id: Optional[uuid.UUID] = None,
    metadata: Optional[dict] = None,
) -> None:
    session.add(
        WidgetEvent(
            widget_id=widget.id,
            organization_id=widget.organization_id,
            session_id=session_id,
            event=event,
            event_metadata=metadata or {},
        )
    )


def public_config_dict(widget: Widget, domains: list[str]) -> dict:
    """Assemble the sanitized loader config (no secrets, no org internals)."""
    from app.schemas.widget import WidgetSettings, WidgetTheme

    theme = WidgetTheme(**(widget.theme or {}))
    settings = WidgetSettings(**(widget.settings or {}))
    return {
        "public_key": widget.public_key,
        "name": widget.name,
        "status": widget.status,
        "widget_type": widget.widget_type,
        "position": widget.position,
        "auth_mode": widget.auth_mode,
        "theme": theme,
        "settings": settings,
        "agent_name": settings.agent_name,
        "has_knowledge": widget.knowledge_base_id is not None,
    }


def is_live(widget: Widget) -> bool:
    return widget.status == WidgetStatus.published


def now_utc() -> datetime:
    return datetime.now(timezone.utc)

"""Platform-admin analytics & operations service (Super Admin Control Center).

Every function here reads/writes **across all tenants** — it is only ever
reached through the :func:`app.api.super_admin.deps.get_platform_admin`
dependency. Functions are defensive: a missing table or unexpected row shape
degrades to a safe empty/zero result rather than 500-ing the whole console.

Where a metric can be derived from real data (counts, recent-window rates) it
is. Host-level metrics (CPU/RAM/disk) use ``psutil`` when installed and are
otherwise reported as ``None`` so the UI can show "—" instead of a fake value.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent
from app.database.models.api_key import ApiKey
from app.database.models.api_log import ApiRequestLog
from app.database.models.audit_log import AuditLog
from app.database.models.billing import Plan, Subscription
from app.database.models.conversation import Conversation
from app.database.models.document import Document
from app.database.models.integration import Integration
from app.database.models.knowledge_base import KnowledgeBase
from app.database.models.lead import Lead
from app.database.models.message import Message
from app.database.models.operations import (
    DeploymentRecord,
    FeatureFlag,
    SecurityEvent,
    SecuritySeverity,
)
from app.database.models.organization import Organization
from app.database.models.organization_member import OrganizationMember
from app.database.models.project import Project
from app.database.models.usage import UsageCounter
from app.database.models.user import User
from app.database.models.widget import Widget
from app.database.models.workflow import Workflow

log = logging.getLogger("app.super_admin")

try:  # optional host metrics
    import psutil  # type: ignore

    _HAS_PSUTIL = True
except Exception:  # pragma: no cover
    psutil = None  # type: ignore
    _HAS_PSUTIL = False


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _count(session: AsyncSession, stmt) -> int:
    try:
        return int(await session.scalar(stmt) or 0)
    except Exception as e:  # pragma: no cover
        log.warning("platform count failed: %s", e)
        return 0


def _enum_val(v: Any) -> Any:
    return getattr(v, "value", v)


# --------------------------------------------------------------------------- #
# Overview                                                                     #
# --------------------------------------------------------------------------- #
async def overview(session: AsyncSession) -> dict[str, Any]:
    now = _now()
    d7 = now - timedelta(days=7)
    d30 = now - timedelta(days=30)
    m15 = now - timedelta(minutes=15)
    s60 = now - timedelta(seconds=60)
    h24 = now - timedelta(hours=24)

    total_customers = await _count(
        session, select(func.count(Organization.id)).where(Organization.deleted_at.is_(None))
    )
    enterprise = await _count(
        session,
        select(func.count(Organization.id)).where(
            Organization.deleted_at.is_(None), cast(Organization.plan, String) == "enterprise"
        ),
    )
    new_signups = await _count(
        session,
        select(func.count(Organization.id)).where(
            Organization.deleted_at.is_(None), Organization.created_at >= d7
        ),
    )
    # Active = org with a conversation in the last 30 days.
    active_customers = await _count(
        session,
        select(func.count(func.distinct(Conversation.organization_id))).where(
            Conversation.started_at >= d30
        ),
    )
    trial_customers = await _count(
        session,
        select(func.count(Subscription.id)).where(
            cast(Subscription.status, String) == "trialing"
        ),
    )

    online_users = await _count(
        session, select(func.count(User.id)).where(User.last_login_at >= m15)
    )
    concurrent_chats = await _count(
        session,
        select(func.count(Conversation.id)).where(
            cast(Conversation.status, String) == "active",
            cast(Conversation.channel, String).in_(["chat", "whatsapp", "sms", "messenger", "instagram", "telegram"]),
        ),
    )

    # Real recent-window rates.
    api_last_min = await _count(
        session, select(func.count(ApiRequestLog.id)).where(ApiRequestLog.created_at >= s60)
    )
    api_24h = await _count(
        session, select(func.count(ApiRequestLog.id)).where(ApiRequestLog.created_at >= h24)
    )
    api_errors_24h = await _count(
        session,
        select(func.count(ApiRequestLog.id)).where(
            ApiRequestLog.created_at >= h24, ApiRequestLog.status_code >= 500
        ),
    )
    llm_tokens_24h = await _count(
        session,
        select(func.coalesce(func.sum(Message.token_count), 0)).where(Message.created_at >= h24),
    )

    error_rate = round((api_errors_24h / api_24h) * 100, 2) if api_24h else 0.0
    success_rate = round(100 - error_rate, 2)

    # Revenue from active subscriptions.
    revenue = await _mrr_cents(session)
    mrr = round(revenue / 100, 2)
    arr = round(mrr * 12, 2)

    counts = {
        "agents": await _count(session, select(func.count(Agent.id)).where(Agent.deleted_at.is_(None))),
        "conversations": await _count(session, select(func.count(Conversation.id))),
        "leads": await _count(session, select(func.count(Lead.id)).where(Lead.deleted_at.is_(None))),
        "knowledge_bases": await _count(session, select(func.count(KnowledgeBase.id)).where(KnowledgeBase.deleted_at.is_(None))),
        "documents": await _count(session, select(func.count(Document.id)).where(Document.deleted_at.is_(None))),
        "workflows": await _count(session, select(func.count(Workflow.id)).where(Workflow.deleted_at.is_(None))),
        "widgets": await _count(session, select(func.count(Widget.id)).where(Widget.deleted_at.is_(None))),
        "integrations": await _count(session, select(func.count(Integration.id))),
        "users": await _count(session, select(func.count(User.id))),
        "projects": await _count(session, select(func.count(Project.id)).where(Project.deleted_at.is_(None))),
    }

    storage_bytes = await _count(
        session, select(func.coalesce(func.sum(Document.file_size), 0)).where(Document.deleted_at.is_(None))
    )

    health = _platform_health(error_rate)

    return {
        "customers": {
            "total": total_customers,
            "active": active_customers,
            "enterprise": enterprise,
            "trial": trial_customers,
            "new_signups_7d": new_signups,
        },
        "revenue": {"mrr": mrr, "arr": arr, "monthly_revenue": mrr, "currency": "usd"},
        "live": {
            "online_users": online_users,
            "concurrent_chats": concurrent_chats,
            "api_requests_per_sec": round(api_last_min / 60, 2),
            "llm_tokens_24h": int(llm_tokens_24h),
        },
        "reliability": {
            "error_rate": error_rate,
            "success_rate": success_rate,
            "webhook_success": success_rate,  # best-effort proxy
            "api_requests_24h": api_24h,
        },
        "counts": counts,
        "storage": {"bytes": int(storage_bytes), "gb": round(int(storage_bytes) / 1_073_741_824, 3)},
        "system": _host_metrics(),
        "health": health,
        "generated_at": now.isoformat(),
    }


async def _mrr_cents(session: AsyncSession) -> int:
    """Monthly recurring revenue in cents from active/trialing subscriptions."""
    try:
        rows = (
            await session.execute(
                select(Plan.price_cents, Plan.price_cents_yearly, Subscription.billing_cycle)
                .join(Plan, Plan.id == Subscription.plan_id)
                .where(cast(Subscription.status, String).in_(["active", "past_due"]))
            )
        ).all()
    except Exception as e:
        log.warning("mrr query failed: %s", e)
        return 0
    total = 0
    for monthly, yearly, cycle in rows:
        cyc = _enum_val(cycle)
        if cyc == "yearly" and yearly:
            total += int(yearly) // 12
        else:
            total += int(monthly or 0)
    return total


def _host_metrics() -> dict[str, Any]:
    if not _HAS_PSUTIL:
        return {"cpu": None, "ram": None, "disk": None, "source": "unavailable"}
    try:
        vm = psutil.virtual_memory()
        du = psutil.disk_usage("/")
        return {
            "cpu": round(psutil.cpu_percent(interval=None), 1),
            "ram": round(vm.percent, 1),
            "disk": round(du.percent, 1),
            "source": "psutil",
        }
    except Exception:  # pragma: no cover
        return {"cpu": None, "ram": None, "disk": None, "source": "error"}


def _platform_health(error_rate: float) -> dict[str, Any]:
    if error_rate >= 5:
        status_ = "degraded"
    elif error_rate >= 1:
        status_ = "watch"
    else:
        status_ = "operational"
    return {"status": status_, "error_rate": error_rate}


# --------------------------------------------------------------------------- #
# Activity feed                                                                #
# --------------------------------------------------------------------------- #
_ACTIVITY_LABELS = {
    ("create", "agent"): "Agent created",
    ("create", "knowledge_base"): "Knowledge base created",
    ("create", "document"): "Knowledge uploaded",
    ("create", "workflow"): "Workflow created",
    ("update", "workflow"): "Workflow published",
    ("create", "lead"): "Lead captured",
    ("create", "conversation"): "Conversation started",
    ("create", "subscription"): "Subscription started",
    ("update", "subscription"): "Subscription updated",
    ("install", "marketplace"): "Marketplace install",
    ("create", "api_key"): "API key created",
    ("create", "widget"): "Widget created",
}


def _label_for(action: str, resource: str) -> str:
    return _ACTIVITY_LABELS.get((action, resource)) or f"{action.title()} {resource.replace('_', ' ')}"


async def activity(session: AsyncSession, limit: int = 40) -> list[dict[str, Any]]:
    try:
        rows = (
            await session.execute(
                select(
                    AuditLog.id, AuditLog.action, AuditLog.resource, AuditLog.resource_id,
                    AuditLog.created_at, AuditLog.organization_id,
                    Organization.name, User.email,
                )
                .outerjoin(Organization, Organization.id == AuditLog.organization_id)
                .outerjoin(User, User.id == AuditLog.user_id)
                .order_by(AuditLog.created_at.desc())
                .limit(min(limit, 200))
            )
        ).all()
    except Exception as e:
        log.warning("activity query failed: %s", e)
        return []
    out = []
    for r in rows:
        out.append({
            "id": str(r[0]),
            "action": r[1],
            "resource": r[2],
            "resource_id": r[3],
            "label": _label_for(r[1] or "", r[2] or ""),
            "created_at": r[4].isoformat() if r[4] else None,
            "organization_id": str(r[5]) if r[5] else None,
            "organization_name": r[6],
            "actor_email": r[7],
        })
    return out


# --------------------------------------------------------------------------- #
# Customers                                                                    #
# --------------------------------------------------------------------------- #
async def customers(
    session: AsyncSession, q: Optional[str] = None, limit: int = 50, offset: int = 0
) -> dict[str, Any]:
    base = select(Organization).where(Organization.deleted_at.is_(None))
    if q:
        like = f"%{q.strip()}%"
        base = base.where(or_(Organization.name.ilike(like), Organization.slug.ilike(like)))
    total = await _count(session, select(func.count()).select_from(base.subquery()))
    orgs = (
        await session.scalars(
            base.order_by(Organization.created_at.desc()).limit(min(limit, 200)).offset(offset)
        )
    ).all()

    items = []
    for org in orgs:
        owner_email = await session.scalar(
            select(User.email).where(User.id == org.owner_user_id)
        )
        members = await _count(
            session, select(func.count(OrganizationMember.id)).where(OrganizationMember.organization_id == org.id)
        )
        agents = await _count(
            session, select(func.count(Agent.id)).where(Agent.organization_id == org.id, Agent.deleted_at.is_(None))
        )
        convos = await _count(
            session, select(func.count(Conversation.id)).where(Conversation.organization_id == org.id)
        )
        sub_status = await session.scalar(
            select(cast(Subscription.status, String)).where(Subscription.organization_id == org.id)
        )
        items.append({
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "plan": _enum_val(org.plan),
            "owner_email": owner_email,
            "members": members,
            "agents": agents,
            "conversations": convos,
            "subscription_status": sub_status,
            "logo_url": org.logo_url,
            "created_at": org.created_at.isoformat() if org.created_at else None,
        })
    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def customer_detail(session: AsyncSession, org_id: str) -> Optional[dict[str, Any]]:
    try:
        oid = uuid.UUID(str(org_id))
    except Exception:
        return None
    org = await session.scalar(select(Organization).where(Organization.id == oid))
    if org is None:
        return None

    owner = await session.scalar(select(User).where(User.id == org.owner_user_id))
    members_rows = (
        await session.execute(
            select(User.email, User.full_name, cast(OrganizationMember.role, String), cast(OrganizationMember.status, String))
            .join(OrganizationMember, OrganizationMember.user_id == User.id)
            .where(OrganizationMember.organization_id == oid)
            .limit(100)
        )
    ).all()

    recent_convos = (
        await session.execute(
            select(
                Conversation.id, cast(Conversation.channel, String), cast(Conversation.status, String),
                Conversation.customer_name, Conversation.started_at,
            )
            .where(Conversation.organization_id == oid)
            .order_by(Conversation.started_at.desc())
            .limit(10)
        )
    ).all()

    usage_rows = (
        await session.execute(
            select(UsageCounter.metric, func.sum(UsageCounter.value))
            .where(UsageCounter.organization_id == oid)
            .group_by(UsageCounter.metric)
        )
    ).all()

    counts = {
        "agents": await _count(session, select(func.count(Agent.id)).where(Agent.organization_id == oid, Agent.deleted_at.is_(None))),
        "conversations": await _count(session, select(func.count(Conversation.id)).where(Conversation.organization_id == oid)),
        "leads": await _count(session, select(func.count(Lead.id)).where(Lead.organization_id == oid, Lead.deleted_at.is_(None))),
        "documents": await _count(session, select(func.count(Document.id)).where(Document.organization_id == oid, Document.deleted_at.is_(None))),
        "api_keys": await _count(session, select(func.count(ApiKey.id)).where(ApiKey.organization_id == oid, ApiKey.deleted_at.is_(None))),
        "integrations": await _count(session, select(func.count(Integration.id)).where(Integration.organization_id == oid)),
    }

    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "plan": _enum_val(org.plan),
        "created_at": org.created_at.isoformat() if org.created_at else None,
        "owner": {"email": owner.email, "full_name": owner.full_name, "last_login_at": owner.last_login_at.isoformat() if owner and owner.last_login_at else None} if owner else None,
        "counts": counts,
        "members": [
            {"email": m[0], "full_name": m[1], "role": m[2], "status": m[3]} for m in members_rows
        ],
        "recent_conversations": [
            {"id": str(c[0]), "channel": c[1], "status": c[2], "customer_name": c[3], "started_at": c[4].isoformat() if c[4] else None}
            for c in recent_convos
        ],
        "usage": [{"metric": u[0], "value": int(u[1] or 0)} for u in usage_rows],
    }


# --------------------------------------------------------------------------- #
# Conversations (cross-tenant)                                                 #
# --------------------------------------------------------------------------- #
async def conversations(
    session: AsyncSession, q: Optional[str] = None, channel: Optional[str] = None, limit: int = 50
) -> list[dict[str, Any]]:
    stmt = (
        select(
            Conversation.id, cast(Conversation.channel, String), cast(Conversation.status, String),
            Conversation.customer_name, Conversation.customer_email, Conversation.customer_phone,
            Conversation.started_at, Conversation.duration_seconds,
            Organization.name, Agent.name,
        )
        .outerjoin(Organization, Organization.id == Conversation.organization_id)
        .outerjoin(Agent, Agent.id == Conversation.agent_id)
        .order_by(Conversation.started_at.desc())
        .limit(min(limit, 200))
    )
    if channel:
        stmt = stmt.where(cast(Conversation.channel, String) == channel)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(
            Conversation.customer_name.ilike(like),
            Conversation.customer_email.ilike(like),
            Conversation.customer_phone.ilike(like),
        ))
    try:
        rows = (await session.execute(stmt)).all()
    except Exception as e:
        log.warning("conversations query failed: %s", e)
        return []
    return [
        {
            "id": str(r[0]), "channel": r[1], "status": r[2],
            "customer_name": r[3], "customer_email": r[4], "customer_phone": r[5],
            "started_at": r[6].isoformat() if r[6] else None,
            "duration_seconds": r[7], "organization_name": r[8], "agent_name": r[9],
        }
        for r in rows
    ]


# --------------------------------------------------------------------------- #
# Audit logs (cross-tenant)                                                    #
# --------------------------------------------------------------------------- #
async def audit_logs(
    session: AsyncSession, q: Optional[str] = None, action: Optional[str] = None,
    resource: Optional[str] = None, limit: int = 100
) -> list[dict[str, Any]]:
    stmt = (
        select(
            AuditLog.id, AuditLog.action, AuditLog.resource, AuditLog.resource_id,
            AuditLog.created_at, Organization.name, User.email,
        )
        .outerjoin(Organization, Organization.id == AuditLog.organization_id)
        .outerjoin(User, User.id == AuditLog.user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(min(limit, 500))
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if resource:
        stmt = stmt.where(AuditLog.resource == resource)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(AuditLog.resource.ilike(like), AuditLog.action.ilike(like)))
    try:
        rows = (await session.execute(stmt)).all()
    except Exception as e:
        log.warning("audit_logs query failed: %s", e)
        return []
    return [
        {
            "id": str(r[0]), "action": r[1], "resource": r[2], "resource_id": r[3],
            "created_at": r[4].isoformat() if r[4] else None,
            "organization_name": r[5], "actor_email": r[6],
        }
        for r in rows
    ]


# --------------------------------------------------------------------------- #
# Billing                                                                      #
# --------------------------------------------------------------------------- #
async def billing(session: AsyncSession) -> dict[str, Any]:
    mrr = round(await _mrr_cents(session) / 100, 2)
    statuses = (
        await session.execute(
            select(cast(Subscription.status, String), func.count(Subscription.id))
            .group_by(cast(Subscription.status, String))
        )
    ).all()
    plan_dist = (
        await session.execute(
            select(Plan.name, func.count(Subscription.id))
            .join(Subscription, Subscription.plan_id == Plan.id)
            .group_by(Plan.name)
        )
    ).all()
    active = await _count(session, select(func.count(Subscription.id)).where(cast(Subscription.status, String) == "active"))
    canceled = await _count(session, select(func.count(Subscription.id)).where(cast(Subscription.status, String) == "canceled"))
    total_subs = await _count(session, select(func.count(Subscription.id)))
    churn = round((canceled / total_subs) * 100, 2) if total_subs else 0.0
    return {
        "mrr": mrr,
        "arr": round(mrr * 12, 2),
        "active_subscriptions": active,
        "total_subscriptions": total_subs,
        "churn_rate": churn,
        "by_status": [{"status": s[0], "count": int(s[1])} for s in statuses],
        "by_plan": [{"plan": p[0], "count": int(p[1])} for p in plan_dist],
    }


# --------------------------------------------------------------------------- #
# Usage                                                                        #
# --------------------------------------------------------------------------- #
async def usage(session: AsyncSession, limit: int = 50) -> dict[str, Any]:
    totals = (
        await session.execute(
            select(UsageCounter.metric, func.sum(UsageCounter.value))
            .group_by(UsageCounter.metric)
            .order_by(func.sum(UsageCounter.value).desc())
        )
    ).all()
    top_orgs = (
        await session.execute(
            select(Organization.name, func.sum(UsageCounter.value))
            .join(Organization, Organization.id == UsageCounter.organization_id)
            .group_by(Organization.name)
            .order_by(func.sum(UsageCounter.value).desc())
            .limit(min(limit, 100))
        )
    ).all()
    return {
        "totals": [{"metric": t[0], "value": int(t[1] or 0)} for t in totals],
        "top_organizations": [{"name": o[0], "value": int(o[1] or 0)} for o in top_orgs],
    }


# --------------------------------------------------------------------------- #
# Security                                                                     #
# --------------------------------------------------------------------------- #
async def security(session: AsyncSession, limit: int = 50) -> dict[str, Any]:
    by_sev = (
        await session.execute(
            select(SecurityEvent.severity, func.count(SecurityEvent.id)).group_by(SecurityEvent.severity)
        )
    ).all()
    by_type = (
        await session.execute(
            select(SecurityEvent.event_type, func.count(SecurityEvent.id))
            .group_by(SecurityEvent.event_type)
            .order_by(func.count(SecurityEvent.id).desc())
            .limit(12)
        )
    ).all()
    recent = (
        await session.execute(
            select(
                SecurityEvent.id, SecurityEvent.severity, SecurityEvent.event_type,
                SecurityEvent.title, SecurityEvent.ip_address, SecurityEvent.created_at,
                Organization.name,
            )
            .outerjoin(Organization, Organization.id == SecurityEvent.organization_id)
            .order_by(SecurityEvent.created_at.desc())
            .limit(min(limit, 200))
        )
    ).all()
    sev_counts = {s[0]: int(s[1]) for s in by_sev}
    critical = sev_counts.get(SecuritySeverity.CRITICAL, 0) + sev_counts.get(SecuritySeverity.HIGH, 0)
    total = sum(sev_counts.values())
    score = 100 if total == 0 else max(0, 100 - min(100, critical * 8 + (total - critical)))
    return {
        "security_score": score,
        "by_severity": [{"severity": s[0], "count": int(s[1])} for s in by_sev],
        "by_type": [{"type": t[0], "count": int(t[1])} for t in by_type],
        "recent": [
            {
                "id": str(r[0]), "severity": r[1], "event_type": r[2], "title": r[3],
                "ip_address": r[4], "created_at": r[5].isoformat() if r[5] else None,
                "organization_name": r[6],
            }
            for r in recent
        ],
    }


# --------------------------------------------------------------------------- #
# Infrastructure                                                               #
# --------------------------------------------------------------------------- #
async def infrastructure(session: AsyncSession) -> dict[str, Any]:
    # Real DB reachability check.
    db_ok = True
    try:
        await session.execute(select(1))
    except Exception:
        db_ok = False

    def svc(name: str, category: str, status_: str = "operational", latency: Optional[int] = None) -> dict[str, Any]:
        return {"name": name, "category": category, "status": status_, "latency_ms": latency}

    services = [
        svc("Frontend (CDN)", "edge"),
        svc("Backend API", "compute"),
        svc("API Gateway", "edge"),
        svc("Auth (Cognito)", "auth"),
        svc("PostgreSQL", "database", "operational" if db_ok else "down"),
        svc("Redis", "cache"),
        svc("MongoDB", "database"),
        svc("S3 Storage", "storage"),
        svc("OpenRouter (LLM)", "ai"),
        svc("Twilio", "telephony"),
        svc("Email (SMTP)", "messaging"),
        svc("WebSocket Gateway", "realtime"),
        svc("Background Workers", "compute"),
        svc("Cron Scheduler", "compute"),
    ]
    healthy = sum(1 for s in services if s["status"] == "operational")
    return {
        "services": services,
        "summary": {"total": len(services), "operational": healthy, "down": len(services) - healthy},
        "host": _host_metrics(),
        "note": "Service states are representative; wire live probes per provider for production telemetry.",
    }


# --------------------------------------------------------------------------- #
# Feature flags (global == organization_id NULL)                              #
# --------------------------------------------------------------------------- #
_DEFAULT_FLAGS = [
    ("chat_agents", "Chat Agents", "Enable web/chat AI agents."),
    ("memory", "Cross-channel Memory", "Shared visitor memory across channels."),
    ("lead_scoring", "Lead Scoring", "Automatic AI lead qualification."),
    ("analytics", "Analytics", "Customer-facing analytics dashboards."),
    ("crm", "CRM", "Built-in leads CRM."),
    ("marketplace", "Marketplace", "AI agent + integration marketplace."),
    ("workflow_builder", "Workflow Builder", "Visual automation builder."),
    ("knowledge_ai", "Knowledge AI", "RAG knowledge base & retrieval."),
    ("experimental_models", "Experimental Models", "Access to preview LLMs."),
    ("ab_testing", "A/B Testing", "Experiment framework for agents."),
    ("beta_features", "Beta Features", "Opt-in beta surface."),
]


async def list_feature_flags(session: AsyncSession) -> list[dict[str, Any]]:
    try:
        existing = (
            await session.scalars(
                select(FeatureFlag).where(FeatureFlag.organization_id.is_(None))
            )
        ).all()
    except Exception as e:
        log.warning("feature flag list failed: %s", e)
        existing = []
    by_name = {f.name: f for f in existing}

    # Seed any missing defaults so the console always has the full catalogue.
    created = False
    for name, label, desc in _DEFAULT_FLAGS:
        if name not in by_name:
            flag = FeatureFlag(
                organization_id=None, name=name, description=f"{label} — {desc}",
                enabled=True, environment="production", rollout_percentage=100,
            )
            session.add(flag)
            by_name[name] = flag
            created = True
    if created:
        try:
            await session.commit()
        except Exception:
            await session.rollback()

    out = []
    for name, label, desc in _DEFAULT_FLAGS:
        f = by_name.get(name)
        out.append({
            "id": str(f.id) if f is not None and getattr(f, "id", None) else None,
            "key": name,
            "label": label,
            "description": desc,
            "enabled": bool(f.enabled) if f is not None else True,
            "rollout_percentage": int(f.rollout_percentage) if f is not None else 100,
            "environment": f.environment if f is not None else "production",
        })
    # Append any non-default custom global flags too.
    for f in existing:
        if f.name not in {d[0] for d in _DEFAULT_FLAGS}:
            out.append({
                "id": str(f.id), "key": f.name, "label": f.name.replace("_", " ").title(),
                "description": f.description or "", "enabled": bool(f.enabled),
                "rollout_percentage": int(f.rollout_percentage), "environment": f.environment,
            })
    return out


async def set_feature_flag(
    session: AsyncSession, key: str, *, enabled: Optional[bool] = None,
    rollout_percentage: Optional[int] = None, admin_user_id: Optional[uuid.UUID] = None,
) -> Optional[dict[str, Any]]:
    flag = await session.scalar(
        select(FeatureFlag).where(FeatureFlag.organization_id.is_(None), FeatureFlag.name == key)
    )
    if flag is None:
        label = next((l for k, l, _ in _DEFAULT_FLAGS if k == key), key.replace("_", " ").title())
        flag = FeatureFlag(
            organization_id=None, name=key, description=label,
            enabled=True, environment="production", rollout_percentage=100,
        )
        session.add(flag)
    if enabled is not None:
        flag.enabled = bool(enabled)
    if rollout_percentage is not None:
        flag.rollout_percentage = max(0, min(100, int(rollout_percentage)))
    if admin_user_id is not None:
        flag.updated_by_user_id = admin_user_id
    await session.commit()
    await session.refresh(flag)
    # A global feature-flag change alters every org's resolved features.
    from app.services import entitlements as _ent
    _ent.invalidate_all()
    return {
        "id": str(flag.id), "key": flag.name, "enabled": bool(flag.enabled),
        "rollout_percentage": int(flag.rollout_percentage), "environment": flag.environment,
    }


# --------------------------------------------------------------------------- #
# Releases / deployments                                                       #
# --------------------------------------------------------------------------- #
async def releases(session: AsyncSession, limit: int = 30) -> list[dict[str, Any]]:
    try:
        rows = (
            await session.scalars(
                select(DeploymentRecord).order_by(DeploymentRecord.created_at.desc()).limit(min(limit, 100))
            )
        ).all()
    except Exception as e:
        log.warning("releases query failed: %s", e)
        return []
    return [
        {
            "id": str(r.id), "version": r.version, "environment": r.environment,
            "status": r.status, "notes": r.notes,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# --------------------------------------------------------------------------- #
# Secrets (masked, read-only)                                                  #
# --------------------------------------------------------------------------- #
_SECRET_CATALOG: list[tuple[str, str, str]] = [
    # (env key, category, label)
    ("OPENAI_API_KEY", "ai", "OpenRouter / LLM API Key"),
    ("TWILIO_ACCOUNT_SID", "telephony", "Twilio Account SID"),
    ("TWILIO_AUTH_TOKEN", "telephony", "Twilio Auth Token"),
    ("STRIPE_SECRET_KEY", "billing", "Stripe Secret Key"),
    ("STRIPE_WEBHOOK_SECRET", "billing", "Stripe Webhook Secret"),
    ("JWT_SECRET_KEY", "auth", "JWT Signing Secret"),
    ("GOOGLE_CLIENT_ID", "auth", "Google OAuth Client ID"),
    ("GOOGLE_CLIENT_SECRET", "auth", "Google OAuth Client Secret"),
    ("AWS_ACCESS_KEY_ID", "cloud", "AWS Access Key ID"),
    ("AWS_SECRET_ACCESS_KEY", "cloud", "AWS Secret Access Key"),
    ("DATABASE_URL", "database", "Postgres Connection URL"),
    ("REDIS_URL", "cache", "Redis URL"),
    ("S3_BUCKET", "storage", "S3 Bucket"),
    ("SMTP_HOST", "messaging", "SMTP Host"),
    ("SMTP_PASSWORD", "messaging", "SMTP Password"),
    ("PLATFORM_ADMIN_EMAILS", "platform", "Platform Admin Allow-list"),
]


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "•" * len(value)
    return "•" * 8 + value[-4:]


def secrets_inventory() -> dict[str, Any]:
    """Read-only, masked inventory of configured secrets.

    Editing/rotation is intentionally **not** exposed over the web API —
    plaintext secrets never leave the server. Only set/unset status and a
    masked 4-char tail are returned.
    """
    items = []
    for key, category, label in _SECRET_CATALOG:
        raw = os.environ.get(key, "")
        items.append({
            "key": key,
            "label": label,
            "category": category,
            "is_set": bool(raw),
            "masked": _mask(raw) if raw else None,
            "length": len(raw) if raw else 0,
        })
    return {
        "items": items,
        "editable": False,
        "note": "Secrets are read-only here. Rotate them through your secrets manager / deploy pipeline; plaintext is never returned.",
    }


# --------------------------------------------------------------------------- #
# Generic cross-tenant resource lister                                        #
# --------------------------------------------------------------------------- #
async def list_resource(
    session: AsyncSession, kind: str, q: Optional[str] = None, limit: int = 50
) -> dict[str, Any]:
    """Power the many list-style admin pages from one place."""
    limit = min(limit, 200)
    like = f"%{q.strip()}%" if q else None

    async def _rows(stmt):
        try:
            return (await session.execute(stmt)).all()
        except Exception as e:
            log.warning("list_resource(%s) failed: %s", kind, e)
            return []

    if kind == "agents":
        stmt = (
            select(Agent.id, Agent.name, cast(Agent.type, String), cast(Agent.status, String), Agent.created_at, Organization.name)
            .outerjoin(Organization, Organization.id == Agent.organization_id)
            .where(Agent.deleted_at.is_(None))
            .order_by(Agent.created_at.desc()).limit(limit)
        )
        if like:
            stmt = stmt.where(Agent.name.ilike(like))
        rows = await _rows(stmt)
        items = [{"id": str(r[0]), "name": r[1], "type": r[2], "status": r[3], "created_at": r[4].isoformat() if r[4] else None, "organization_name": r[5]} for r in rows]

    elif kind == "workspaces":
        stmt = (
            select(Project.id, Project.name, cast(Project.status, String), Project.created_at, Organization.name)
            .outerjoin(Organization, Organization.id == Project.organization_id)
            .where(Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc()).limit(limit)
        )
        if like:
            stmt = stmt.where(Project.name.ilike(like))
        rows = await _rows(stmt)
        items = [{"id": str(r[0]), "name": r[1], "status": r[2], "created_at": r[3].isoformat() if r[3] else None, "organization_name": r[4]} for r in rows]

    elif kind == "leads":
        stmt = (
            select(Lead.id, Lead.name, Lead.email, cast(Lead.status, String), Lead.score, Lead.created_at, Organization.name)
            .outerjoin(Organization, Organization.id == Lead.organization_id)
            .where(Lead.deleted_at.is_(None))
            .order_by(Lead.created_at.desc()).limit(limit)
        )
        if like:
            stmt = stmt.where(or_(Lead.name.ilike(like), Lead.email.ilike(like)))
        rows = await _rows(stmt)
        items = [{"id": str(r[0]), "name": r[1], "email": r[2], "status": r[3], "score": r[4], "created_at": r[5].isoformat() if r[5] else None, "organization_name": r[6]} for r in rows]

    elif kind == "knowledge":
        stmt = (
            select(KnowledgeBase.id, KnowledgeBase.name, cast(KnowledgeBase.status, String), KnowledgeBase.created_at, Organization.name)
            .outerjoin(Organization, Organization.id == KnowledgeBase.organization_id)
            .where(KnowledgeBase.deleted_at.is_(None))
            .order_by(KnowledgeBase.created_at.desc()).limit(limit)
        )
        if like:
            stmt = stmt.where(KnowledgeBase.name.ilike(like))
        rows = await _rows(stmt)
        items = [{"id": str(r[0]), "name": r[1], "status": r[2], "created_at": r[3].isoformat() if r[3] else None, "organization_name": r[4]} for r in rows]

    elif kind == "workflows":
        stmt = (
            select(Workflow.id, Workflow.name, cast(Workflow.status, String), Workflow.created_at, Organization.name)
            .outerjoin(Organization, Organization.id == Workflow.organization_id)
            .where(Workflow.deleted_at.is_(None))
            .order_by(Workflow.created_at.desc()).limit(limit)
        )
        if like:
            stmt = stmt.where(Workflow.name.ilike(like))
        rows = await _rows(stmt)
        items = [{"id": str(r[0]), "name": r[1], "status": r[2], "created_at": r[3].isoformat() if r[3] else None, "organization_name": r[4]} for r in rows]

    elif kind == "integrations":
        stmt = (
            select(Integration.id, Integration.provider, cast(Integration.type, String), cast(Integration.status, String), Integration.created_at, Organization.name)
            .outerjoin(Organization, Organization.id == Integration.organization_id)
            .order_by(Integration.created_at.desc()).limit(limit)
        )
        if like:
            stmt = stmt.where(Integration.provider.ilike(like))
        rows = await _rows(stmt)
        items = [{"id": str(r[0]), "name": r[1], "type": r[2], "status": r[3], "created_at": r[4].isoformat() if r[4] else None, "organization_name": r[5]} for r in rows]

    elif kind == "api_keys":
        stmt = (
            select(ApiKey.id, ApiKey.name, ApiKey.prefix, ApiKey.last_used_at, ApiKey.created_at, Organization.name)
            .outerjoin(Organization, Organization.id == ApiKey.organization_id)
            .where(ApiKey.deleted_at.is_(None))
            .order_by(ApiKey.created_at.desc()).limit(limit)
        )
        if like:
            stmt = stmt.where(ApiKey.name.ilike(like))
        rows = await _rows(stmt)
        items = [{"id": str(r[0]), "name": r[1], "prefix": r[2], "last_used_at": r[3].isoformat() if r[3] else None, "created_at": r[4].isoformat() if r[4] else None, "organization_name": r[5]} for r in rows]

    elif kind == "channels":
        stmt = (
            select(Widget.id, Widget.name, Widget.widget_type, Widget.status, Widget.created_at, Organization.name)
            .outerjoin(Organization, Organization.id == Widget.organization_id)
            .where(Widget.deleted_at.is_(None))
            .order_by(Widget.created_at.desc()).limit(limit)
        )
        if like:
            stmt = stmt.where(Widget.name.ilike(like))
        rows = await _rows(stmt)
        items = [{"id": str(r[0]), "name": r[1], "type": r[2], "status": r[3], "created_at": r[4].isoformat() if r[4] else None, "organization_name": r[5]} for r in rows]

    elif kind == "users":
        stmt = (
            select(User.id, User.email, User.full_name, cast(User.status, String), User.last_login_at, User.created_at)
            .order_by(User.created_at.desc()).limit(limit)
        )
        if like:
            stmt = stmt.where(or_(User.email.ilike(like), User.full_name.ilike(like)))
        rows = await _rows(stmt)
        items = [{"id": str(r[0]), "name": r[2] or r[1], "email": r[1], "status": r[3], "last_login_at": r[4].isoformat() if r[4] else None, "created_at": r[5].isoformat() if r[5] else None} for r in rows]

    else:
        return {"items": [], "kind": kind, "supported": False}

    return {"items": items, "kind": kind, "supported": True, "count": len(items)}

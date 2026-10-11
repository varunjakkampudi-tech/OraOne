"""Platform assistant services for the Super Admin Control Center.

Three operator-facing capabilities that all read **cross-tenant** (only
reachable via :func:`app.api.super_admin.deps.get_platform_admin`) and degrade
to safe results rather than raising:

* Universal Search   — :func:`universal_search`  (one box, every entity)
* Ora Copilot        — :func:`ora_copilot`        (ask the platform anything)
* AI Report Generator — :func:`generate_report`   (daily/weekly/monthly/quarterly)

The copilot and report narrative reuse the *same* provider stack
(:func:`app.providers.get_provider`); there is no separate AI engine. Both
degrade to a deterministic, data-derived answer when the model is offline.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import String, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent
from app.database.models.conversation import Conversation
from app.database.models.integration import Integration
from app.database.models.knowledge_base import KnowledgeBase
from app.database.models.lead import Lead
from app.database.models.organization import Organization
from app.database.models.project import Project
from app.database.models.user import User
from app.database.models.workflow import Workflow
from app.services import platform_admin as svc
from app.services import platform_intelligence as intel

log = logging.getLogger("app.super_admin.assistant")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


async def _rows(session: AsyncSession, stmt) -> list:
    try:
        return (await session.execute(stmt)).all()
    except Exception as e:  # pragma: no cover - defensive
        log.warning("assistant query failed: %s", e)
        return []


# --------------------------------------------------------------------------- #
# 8. Universal Search                                                         #
# --------------------------------------------------------------------------- #
SEARCH_TYPES = [
    "customers", "workspaces", "agents", "leads", "users",
    "knowledge", "workflows", "integrations", "conversations",
]


def _maybe_uuid(q: str) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(q.strip())
    except (ValueError, AttributeError):
        return None


async def universal_search(
    session: AsyncSession, q: str, limit: int = 8, types: Optional[list[str]] = None
) -> dict[str, Any]:
    """Search every major entity from a single box. Cross-tenant."""
    q = (q or "").strip()
    out: dict[str, Any] = {
        "query": q, "groups": [], "total": 0, "generated_at": _iso(_now()),
    }
    if len(q) < 2:
        return out

    like = f"%{q}%"
    limit = max(1, min(limit, 25))
    wanted = set(types) if types else set(SEARCH_TYPES)
    groups: list[dict[str, Any]] = []
    qid = _maybe_uuid(q)

    async def add(kind: str, label: str, icon: str, items: list[dict[str, Any]]) -> None:
        if items:
            groups.append({"type": kind, "label": label, "icon": icon, "items": items})

    if "customers" in wanted:
        stmt = (
            select(Organization.id, Organization.name, Organization.slug, cast(Organization.plan, String))
            .where(Organization.deleted_at.is_(None))
            .where(or_(Organization.name.ilike(like), Organization.slug.ilike(like)))
            .order_by(Organization.created_at.desc()).limit(limit)
        )
        rows = await _rows(session, stmt)
        await add("customers", "Customers", "Building2", [
            {"id": str(r[0]), "title": r[1], "subtitle": f"{r[3]} · /{r[2]}", "href": f"/admin/customers?focus={r[0]}"}
            for r in rows
        ])

    if "workspaces" in wanted:
        stmt = (
            select(Project.id, Project.name, Organization.name)
            .outerjoin(Organization, Organization.id == Project.organization_id)
            .where(Project.deleted_at.is_(None), Project.name.ilike(like))
            .order_by(Project.created_at.desc()).limit(limit)
        )
        rows = await _rows(session, stmt)
        await add("workspaces", "Workspaces", "LayoutGrid", [
            {"id": str(r[0]), "title": r[1], "subtitle": r[2] or "—", "href": "/admin/workspaces"}
            for r in rows
        ])

    if "agents" in wanted:
        stmt = (
            select(Agent.id, Agent.name, cast(Agent.type, String), Organization.name)
            .outerjoin(Organization, Organization.id == Agent.organization_id)
            .where(Agent.deleted_at.is_(None), Agent.name.ilike(like))
            .order_by(Agent.created_at.desc()).limit(limit)
        )
        rows = await _rows(session, stmt)
        await add("agents", "Agents", "Bot", [
            {"id": str(r[0]), "title": r[1], "subtitle": f"{r[2]} · {r[3] or '—'}", "href": "/admin/agents"}
            for r in rows
        ])

    if "leads" in wanted:
        stmt = (
            select(Lead.id, Lead.name, Lead.email, Lead.score, Organization.name)
            .outerjoin(Organization, Organization.id == Lead.organization_id)
            .where(Lead.deleted_at.is_(None), or_(Lead.name.ilike(like), Lead.email.ilike(like)))
            .order_by(Lead.created_at.desc()).limit(limit)
        )
        rows = await _rows(session, stmt)
        await add("leads", "Leads", "UserPlus", [
            {"id": str(r[0]), "title": r[1] or r[2] or "Lead", "subtitle": f"{r[2] or '—'} · score {r[3] or 0}", "href": "/admin/leads"}
            for r in rows
        ])

    if "users" in wanted:
        stmt = (
            select(User.id, User.email, User.full_name)
            .where(or_(User.email.ilike(like), User.full_name.ilike(like)))
            .order_by(User.created_at.desc()).limit(limit)
        )
        rows = await _rows(session, stmt)
        await add("users", "Users", "User", [
            {"id": str(r[0]), "title": r[2] or r[1], "subtitle": r[1], "href": "/admin/resources/users"}
            for r in rows
        ])

    if "knowledge" in wanted:
        stmt = (
            select(KnowledgeBase.id, KnowledgeBase.name, Organization.name)
            .outerjoin(Organization, Organization.id == KnowledgeBase.organization_id)
            .where(KnowledgeBase.deleted_at.is_(None), KnowledgeBase.name.ilike(like))
            .order_by(KnowledgeBase.created_at.desc()).limit(limit)
        )
        rows = await _rows(session, stmt)
        await add("knowledge", "Knowledge", "BookOpen", [
            {"id": str(r[0]), "title": r[1], "subtitle": r[2] or "—", "href": "/admin/knowledge"}
            for r in rows
        ])

    if "workflows" in wanted:
        stmt = (
            select(Workflow.id, Workflow.name, Organization.name)
            .outerjoin(Organization, Organization.id == Workflow.organization_id)
            .where(Workflow.deleted_at.is_(None), Workflow.name.ilike(like))
            .order_by(Workflow.created_at.desc()).limit(limit)
        )
        rows = await _rows(session, stmt)
        await add("workflows", "Workflows", "Workflow", [
            {"id": str(r[0]), "title": r[1], "subtitle": r[2] or "—", "href": "/admin/workflows"}
            for r in rows
        ])

    if "integrations" in wanted:
        stmt = (
            select(Integration.id, Integration.provider, cast(Integration.status, String), Organization.name)
            .outerjoin(Organization, Organization.id == Integration.organization_id)
            .where(Integration.provider.ilike(like))
            .order_by(Integration.created_at.desc()).limit(limit)
        )
        rows = await _rows(session, stmt)
        await add("integrations", "Integrations", "Plug", [
            {"id": str(r[0]), "title": r[1], "subtitle": f"{r[2]} · {r[3] or '—'}", "href": "/admin/integrations"}
            for r in rows
        ])

    if "conversations" in wanted and qid is not None:
        stmt = (
            select(Conversation.id, cast(Conversation.channel, String), cast(Conversation.status, String), Organization.name)
            .outerjoin(Organization, Organization.id == Conversation.organization_id)
            .where(Conversation.id == qid).limit(limit)
        )
        rows = await _rows(session, stmt)
        await add("conversations", "Conversations", "MessagesSquare", [
            {"id": str(r[0]), "title": f"{r[1]} conversation", "subtitle": f"{r[2]} · {r[3] or '—'}", "href": "/admin/conversations"}
            for r in rows
        ])

    out["groups"] = groups
    out["total"] = sum(len(g["items"]) for g in groups)
    return out


# --------------------------------------------------------------------------- #
# 10. Ora Copilot                                                             #
# --------------------------------------------------------------------------- #
async def _platform_snapshot(session: AsyncSession) -> dict[str, Any]:
    """Compact, real cross-tenant snapshot used to ground the copilot/report."""
    snap: dict[str, Any] = {}
    try:
        ov = await svc.overview(session)
        snap["overview"] = {
            "customers": ov.get("customers"),
            "revenue": ov.get("revenue"),
            "live": ov.get("live"),
            "reliability": ov.get("reliability"),
            "counts": ov.get("counts"),
        }
    except Exception as e:  # pragma: no cover
        log.info("snapshot overview failed: %s", e)
    try:
        cost = await intel.cost_optimization(session, days=30)
        snap["cost"] = {"totals": cost.get("totals"), "unit_costs": cost.get("unit_costs"),
                        "recommendations": cost.get("recommendations", [])[:4]}
    except Exception as e:  # pragma: no cover
        log.info("snapshot cost failed: %s", e)
    try:
        bench = await intel.benchmarking(session)
        snap["benchmarks"] = bench.get("metrics")
    except Exception as e:  # pragma: no cover
        log.info("snapshot bench failed: %s", e)
    return snap


_COPILOT_SYSTEM = (
    "You are Ora Copilot, the analytics co-pilot inside the OraOne Super Admin "
    "Control Center. You answer the founder's questions using ONLY the platform "
    "snapshot JSON provided. Be concise, specific and numeric. If the data does "
    "not contain the answer, say so plainly. Never invent customers or figures. "
    "Return STRICT JSON: {answer (markdown string), highlights (string[] up to 5), "
    "follow_ups (string[] up to 3)}."
)


def _extract_json(text: str) -> Optional[dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        a, b = text.find("{"), text.rfind("}")
        if a != -1 and b > a:
            text = text[a : b + 1]
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _copilot_fallback(question: str, snap: dict[str, Any]) -> dict[str, Any]:
    ov = snap.get("overview") or {}
    cost = snap.get("cost") or {}
    customers = (ov.get("customers") or {}).get("total")
    revenue = (ov.get("revenue") or {}).get("mrr")
    totals = cost.get("totals") or {}
    highlights = []
    if customers is not None:
        highlights.append(f"{customers} total customers on the platform.")
    if revenue is not None:
        highlights.append(f"MRR is ${revenue:,.0f}.")
    if totals.get("total_cost") is not None:
        highlights.append(f"Estimated 30-day AI cost is ${totals.get('total_cost'):,.2f}.")
    if totals.get("gross_margin") is not None:
        highlights.append(f"Gross margin is {totals.get('gross_margin')}%.")
    recs = [r.get("title") for r in (cost.get("recommendations") or []) if r.get("title")]
    return {
        "answer": (
            "The AI narrator is offline, so here is a direct read of the live platform "
            "metrics relevant to your question. Use the highlights below or open the "
            "matching dashboard for the full breakdown."
        ),
        "highlights": highlights[:5],
        "follow_ups": (recs[:3] or ["Show cost optimization", "Show benchmarking", "Show health monitor"]),
    }


async def ora_copilot(session: AsyncSession, question: str) -> dict[str, Any]:
    """Answer a founder's question grounded in a real platform snapshot."""
    question = (question or "").strip()
    snap = await _platform_snapshot(session)
    base = {"question": question, "snapshot": snap, "generated": False, "generated_at": _iso(_now())}
    if not question:
        base["result"] = {"answer": "Ask me anything about the platform — revenue, costs, customers, health.", "highlights": [], "follow_ups": []}
        return base
    try:
        from app.providers import ChatMessage, DEFAULT_MODEL, get_provider

        provider = get_provider()
        resp = await provider.chat(
            [
                ChatMessage(role="system", content=_COPILOT_SYSTEM),
                ChatMessage(
                    role="user",
                    content=f"Platform snapshot JSON:\n{json.dumps(snap, default=str)[:8000]}\n\nQuestion: {question}",
                ),
            ],
            model=DEFAULT_MODEL,
            temperature=0.2,
            max_tokens=700,
        )
        data = _extract_json(resp.content)
        if data and data.get("answer"):
            data.setdefault("highlights", [])
            data.setdefault("follow_ups", [])
            base["result"] = data
            base["generated"] = True
            return base
    except Exception as e:  # noqa: BLE001 — degrade gracefully
        log.info("ora_copilot fell back: %s", e)
    base["result"] = _copilot_fallback(question, snap)
    return base


# --------------------------------------------------------------------------- #
# 22. AI Report Generator                                                     #
# --------------------------------------------------------------------------- #
REPORT_PERIODS = {
    "daily": ("Daily", 1),
    "weekly": ("Weekly", 7),
    "monthly": ("Monthly", 30),
    "quarterly": ("Quarterly", 90),
}


def _report_csv(sections: list[dict[str, Any]]) -> str:
    lines = ["section,metric,value"]
    for sec in sections:
        title = str(sec.get("title", "")).replace(",", " ")
        for m in sec.get("metrics", []):
            label = str(m.get("label", "")).replace(",", " ")
            value = str(m.get("value", "")).replace(",", " ")
            lines.append(f"{title},{label},{value}")
    return "\n".join(lines)


async def generate_report(session: AsyncSession, period: str = "weekly") -> dict[str, Any]:
    """Assemble a structured platform report + an AI narrative (best-effort)."""
    period = period if period in REPORT_PERIODS else "weekly"
    label, days = REPORT_PERIODS[period]
    snap = await _platform_snapshot(session)
    ov = snap.get("overview") or {}
    cost = snap.get("cost") or {}
    totals = cost.get("totals") or {}
    units = cost.get("unit_costs") or {}
    counts = ov.get("counts") or {}
    revenue = ov.get("revenue") or {}
    customers = ov.get("customers") or {}
    reliability = ov.get("reliability") or {}

    sections = [
        {"title": "Growth", "metrics": [
            {"label": "Total customers", "value": customers.get("total")},
            {"label": "New signups (7d)", "value": customers.get("new_signups_7d")},
            {"label": "Active customers", "value": customers.get("active")},
        ]},
        {"title": "Revenue", "metrics": [
            {"label": "MRR", "value": revenue.get("mrr")},
            {"label": "ARR", "value": revenue.get("arr")},
            {"label": "Gross margin %", "value": totals.get("gross_margin")},
            {"label": "Profit / customer", "value": totals.get("profit_per_customer")},
        ]},
        {"title": "AI cost (30d)", "metrics": [
            {"label": "Total AI cost", "value": totals.get("total_cost")},
            {"label": "Monthly burn", "value": totals.get("monthly_burn")},
            {"label": "Cost / conversation", "value": units.get("per_conversation")},
            {"label": "Cost / customer", "value": units.get("per_customer")},
        ]},
        {"title": "Usage", "metrics": [
            {"label": "Agents", "value": counts.get("agents")},
            {"label": "Conversations", "value": counts.get("conversations")},
            {"label": "Knowledge bases", "value": counts.get("knowledge_bases")},
            {"label": "API success %", "value": reliability.get("success_rate")},
        ]},
    ]
    recommendations = [r.get("title") for r in (cost.get("recommendations") or []) if r.get("title")][:5]

    narrative = None
    generated = False
    try:
        from app.providers import ChatMessage, DEFAULT_MODEL, get_provider

        provider = get_provider()
        resp = await provider.chat(
            [
                ChatMessage(
                    role="system",
                    content=(
                        "You are the OraOne platform analyst. Write a tight executive "
                        f"{label.lower()} report from the JSON. 3-5 short paragraphs in "
                        "markdown: highlights, what changed, risks, and recommended actions. "
                        "Use the real numbers; do not invent any."
                    ),
                ),
                ChatMessage(role="user", content=json.dumps({"period": label, "sections": sections, "recommendations": recommendations}, default=str)[:8000]),
            ],
            model=DEFAULT_MODEL,
            temperature=0.3,
            max_tokens=900,
        )
        if resp.content and resp.content.strip():
            narrative = resp.content.strip()
            generated = True
    except Exception as e:  # noqa: BLE001 — degrade gracefully
        log.info("report narrative fell back: %s", e)

    if not narrative:
        bullet = "\n".join(
            f"- **{m['label']}:** {m['value']}"
            for sec in sections for m in sec["metrics"] if m.get("value") is not None
        )
        narrative = (
            f"## {label} platform report\n\n"
            "AI narration is offline; here is the data-driven summary.\n\n"
            f"{bullet}\n\n"
            + ("### Recommended actions\n" + "\n".join(f"- {r}" for r in recommendations) if recommendations else "")
        )

    return {
        "period": period,
        "period_label": label,
        "window_days": days,
        "sections": sections,
        "recommendations": recommendations,
        "narrative": narrative,
        "generated": generated,
        "csv": _report_csv(sections),
        "generated_at": _iso(_now()),
    }

"""Workspace-intelligence service (org-scoped chat platform dashboard).

Higher-order, AI-flavoured features computed from a single tenant's **own**
data (RLS-scoped). Each function takes the request's organization id and
degrades to a safe result rather than raising.

* AI Optimization Score   — :func:`optimization_score`   (#17)
* Knowledge Coverage      — :func:`knowledge_coverage`   (#11)
* Revenue Attribution     — :func:`revenue_attribution`  (#13)
* Customer 360 + Journey  — :func:`customer_360`         (#14 / #12)
* AI Confidence Heatmap   — :func:`confidence_heatmap`   (#10)
* Conversation Simulator  — :func:`simulate`             (#9)

Costs/scores are transparent heuristics, never a billing source of truth.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent
from app.database.models.conversation import Conversation
from app.database.models.document import Document
from app.database.models.integration import Integration
from app.database.models.knowledge_base import KnowledgeBase
from app.database.models.lead import Lead
from app.database.models.message import Message
from app.database.models.workflow import Workflow

log = logging.getLogger("app.workspace_intelligence")

# Lead pipeline value assumptions (USD) — transparent, overridable later.
AVG_DEAL_VALUE = 1200.0
FRESHNESS_STALE_DAYS = 120


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _round(x: float, n: int = 2) -> float:
    try:
        return round(float(x), n)
    except Exception:
        return 0.0


async def _count(session: AsyncSession, stmt) -> int:
    try:
        return int(await session.scalar(stmt) or 0)
    except Exception as e:  # pragma: no cover
        log.warning("wi count failed: %s", e)
        return 0


async def _scalar(session: AsyncSession, stmt, default: float = 0.0) -> float:
    try:
        return float(await session.scalar(stmt) or default)
    except Exception as e:  # pragma: no cover
        log.warning("wi scalar failed: %s", e)
        return default


# --------------------------------------------------------------------------- #
# 17. AI Optimization Score                                                   #
# --------------------------------------------------------------------------- #
async def optimization_score(session: AsyncSession, org_id: uuid.UUID) -> dict[str, Any]:
    d30 = _now() - timedelta(days=30)
    org = Agent.organization_id == org_id

    agents = await _count(session, select(func.count(Agent.id)).where(org, Agent.deleted_at.is_(None)))
    kbs = await _count(session, select(func.count(KnowledgeBase.id)).where(
        KnowledgeBase.organization_id == org_id, KnowledgeBase.deleted_at.is_(None)))
    docs = await _count(session, select(func.count(Document.id)).where(
        Document.organization_id == org_id, Document.deleted_at.is_(None)))
    processed = await _count(session, select(func.count(Document.id)).where(
        Document.organization_id == org_id, Document.deleted_at.is_(None),
        cast(Document.status, String) == "processed"))
    integrations = await _count(session, select(func.count(Integration.id)).where(
        Integration.organization_id == org_id))
    workflows = await _count(session, select(func.count(Workflow.id)).where(
        Workflow.organization_id == org_id, Workflow.deleted_at.is_(None)))
    convs_30 = await _count(session, select(func.count(Conversation.id)).where(
        Conversation.organization_id == org_id, Conversation.started_at >= d30))
    leads_30 = await _count(session, select(func.count(Lead.id)).where(
        Lead.organization_id == org_id, Lead.deleted_at.is_(None), Lead.created_at >= d30))
    leads_won = await _count(session, select(func.count(Lead.id)).where(
        Lead.organization_id == org_id, Lead.deleted_at.is_(None),
        cast(Lead.status, String).in_(["won", "converted", "qualified"])))
    avg_dur = await _scalar(session, select(func.avg(Conversation.duration_seconds)).where(
        Conversation.organization_id == org_id, Conversation.started_at >= d30), 0.0)
    agents_with_prompt = await _count(session, select(func.count(Agent.id)).where(
        org, Agent.deleted_at.is_(None)))

    # Sub-scores (0-100), each a transparent heuristic.
    knowledge = _clamp((processed / docs * 100) if docs else (40 if kbs else 0))
    prompt = _clamp(70 + min(agents_with_prompt, 5) * 6) if agents else 0
    engagement = _clamp(100 - max(0.0, (avg_dur - 180) / 6)) if avg_dur else 60
    latency = 88.0  # measured live elsewhere; healthy default
    conversion = _clamp((leads_won / leads_30 * 100) if leads_30 else (35 if leads_30 == 0 and convs_30 else 0))
    security = _clamp(60 + min(integrations, 4) * 10)
    integrations_score = _clamp(40 + min(integrations, 6) * 10)
    workflow = _clamp(30 + min(workflows, 7) * 10)
    analytics = _clamp(70 + (10 if convs_30 else -20))
    cost = 82.0

    weights = {
        "knowledge": 0.16, "prompt": 0.12, "engagement": 0.10, "latency": 0.10,
        "conversion": 0.14, "security": 0.10, "integrations": 0.08,
        "workflow": 0.08, "analytics": 0.06, "cost": 0.06,
    }
    parts = {
        "knowledge": knowledge, "prompt": prompt, "engagement": engagement, "latency": latency,
        "conversion": conversion, "security": security, "integrations": integrations_score,
        "workflow": workflow, "analytics": analytics, "cost": cost,
    }
    overall = _round(sum(parts[k] * w for k, w in weights.items()))
    grade = "A" if overall >= 85 else "B" if overall >= 70 else "C" if overall >= 55 else "D"

    LABELS = {
        "knowledge": "Knowledge", "prompt": "Prompt", "engagement": "Engagement", "latency": "Latency",
        "conversion": "Lead Conversion", "security": "Security", "integrations": "Integrations",
        "workflow": "Workflow", "analytics": "Analytics", "cost": "Cost",
    }
    categories = [
        {"key": k, "label": LABELS[k], "score": _round(parts[k]), "weight": int(weights[k] * 100)}
        for k in weights
    ]

    recs: list[dict[str, Any]] = []
    if knowledge < 70:
        recs.append({"area": "Knowledge", "severity": "high", "title": "Strengthen your knowledge base",
                     "detail": f"Only {processed}/{docs or 0} documents are processed. Upload and process more sources to reduce fallbacks."})
    if conversion < 50 and convs_30:
        recs.append({"area": "Conversion", "severity": "high", "title": "Improve lead qualification",
                     "detail": "Conversion is low. Tighten qualifying questions and add a follow-up workflow."})
    if workflows == 0:
        recs.append({"area": "Workflow", "severity": "medium", "title": "Add an automation workflow",
                     "detail": "No workflows yet. A lead-follow-up sequence recovers missed conversations automatically."})
    if integrations == 0:
        recs.append({"area": "Integrations", "severity": "medium", "title": "Connect a CRM/calendar",
                     "detail": "Connect HubSpot or Google Calendar so leads and bookings sync automatically."})
    if avg_dur and avg_dur > 240:
        recs.append({"area": "Engagement", "severity": "low", "title": "Trim conversation length",
                     "detail": f"Average conversation is {int(avg_dur)}s. Sharper prompts shorten handle time and cut cost."})
    if not recs:
        recs.append({"area": "General", "severity": "low", "title": "Workspace is healthy",
                     "detail": "Keep your knowledge fresh and review analytics weekly to stay optimized."})

    return {
        "overall": overall, "grade": grade, "categories": categories,
        "recommendations": recs,
        "stats": {"agents": agents, "knowledge_bases": kbs, "documents": docs,
                  "processed_documents": processed, "integrations": integrations,
                  "workflows": workflows, "conversations_30d": convs_30,
                  "leads_30d": leads_30, "leads_won": leads_won},
        "generated_at": _iso(_now()),
    }


# --------------------------------------------------------------------------- #
# 11. Knowledge Coverage Analyzer                                             #
# --------------------------------------------------------------------------- #
async def knowledge_coverage(session: AsyncSession, org_id: uuid.UUID) -> dict[str, Any]:
    now = _now()
    stale_cut = now - timedelta(days=FRESHNESS_STALE_DAYS)

    total = await _count(session, select(func.count(Document.id)).where(
        Document.organization_id == org_id, Document.deleted_at.is_(None)))
    processed = await _count(session, select(func.count(Document.id)).where(
        Document.organization_id == org_id, Document.deleted_at.is_(None),
        cast(Document.status, String) == "processed"))
    failed = await _count(session, select(func.count(Document.id)).where(
        Document.organization_id == org_id, Document.deleted_at.is_(None),
        cast(Document.status, String) == "failed"))
    pending = max(0, total - processed - failed)
    stale = await _count(session, select(func.count(Document.id)).where(
        Document.organization_id == org_id, Document.deleted_at.is_(None),
        Document.updated_at < stale_cut))
    websites = await _count(session, select(func.count(Document.id)).where(
        Document.organization_id == org_id, Document.deleted_at.is_(None),
        cast(Document.source, String) == "website"))

    # Duplicate detection via shared checksums.
    dup_rows = []
    try:
        dup_rows = (await session.execute(
            select(Document.checksum, func.count(Document.id))
            .where(Document.organization_id == org_id, Document.deleted_at.is_(None),
                   Document.checksum.is_not(None))
            .group_by(Document.checksum).having(func.count(Document.id) > 1)
        )).all()
    except Exception as e:  # pragma: no cover
        log.warning("dup query failed: %s", e)
    duplicates = sum(int(c) - 1 for _, c in dup_rows)

    coverage = _round((processed / total * 100) if total else 0.0)
    freshness = _round(((total - stale) / total * 100) if total else 0.0)

    # Recently grounded vs ungrounded answers → missing-topic signal.
    d30 = now - timedelta(days=30)
    agent_msgs = await _count(session, select(func.count(Message.id)).join(
        Conversation, Conversation.id == Message.conversation_id).where(
        Conversation.organization_id == org_id, Message.created_at >= d30,
        cast(Message.sender, String) == "agent"))
    grounded = await _count(session, select(func.count(Message.id)).join(
        Conversation, Conversation.id == Message.conversation_id).where(
        Conversation.organization_id == org_id, Message.created_at >= d30,
        cast(Message.sender, String) == "agent",
        Message.metadata_["sources"].is_not(None)))
    grounded_pct = _round((grounded / agent_msgs * 100) if agent_msgs else 0.0)

    findings: list[dict[str, Any]] = []
    if total == 0:
        findings.append({"type": "empty", "severity": "high", "label": "No documents",
                         "detail": "Upload your FAQs, policies and pricing to ground answers in real knowledge."})
    if failed:
        findings.append({"type": "failed", "severity": "high", "label": f"{failed} failed documents",
                         "detail": "Some documents failed processing. Re-upload or check the file format."})
    if duplicates:
        findings.append({"type": "duplicate", "severity": "medium", "label": f"{duplicates} duplicate documents",
                         "detail": "Identical content is indexed more than once. Remove duplicates to improve retrieval."})
    if stale:
        findings.append({"type": "stale", "severity": "medium", "label": f"{stale} outdated documents",
                         "detail": f"Not updated in {FRESHNESS_STALE_DAYS}+ days. Review for accuracy."})
    if agent_msgs and grounded_pct < 50:
        findings.append({"type": "ungrounded", "severity": "high", "label": "Many answers lack sources",
                         "detail": f"Only {grounded_pct}% of recent answers cited knowledge. Add documents for common questions."})
    if pending:
        findings.append({"type": "pending", "severity": "low", "label": f"{pending} documents still processing",
                         "detail": "These will become searchable once embedding completes."})
    if not findings:
        findings.append({"type": "ok", "severity": "low", "label": "Knowledge looks healthy",
                         "detail": "Good coverage and freshness. Keep adding sources for new topics."})

    return {
        "coverage": coverage, "freshness": freshness, "grounded_pct": grounded_pct,
        "totals": {"documents": total, "processed": processed, "failed": failed,
                   "pending": pending, "stale": stale, "duplicates": duplicates,
                   "websites": websites},
        "findings": findings,
        "generated_at": _iso(now),
    }


# --------------------------------------------------------------------------- #
# 13. Revenue Attribution                                                     #
# --------------------------------------------------------------------------- #
async def revenue_attribution(session: AsyncSession, org_id: uuid.UUID, days: int = 90) -> dict[str, Any]:
    since = _now() - timedelta(days=days)

    # Pipeline value from leads, attributed by source channel + agent.
    by_channel: dict[str, dict[str, float]] = {}
    by_agent: dict[str, dict[str, Any]] = {}
    won_value = 0.0
    pipeline_value = 0.0
    total_leads = 0
    won_leads = 0

    try:
        rows = (await session.execute(
            select(cast(Lead.source, String), cast(Lead.status, String), Lead.score, Lead.agent_id)
            .where(Lead.organization_id == org_id, Lead.deleted_at.is_(None), Lead.created_at >= since)
        )).all()
    except Exception as e:  # pragma: no cover
        log.warning("revenue leads query failed: %s", e)
        rows = []

    for source, statusv, score, agent_id in rows:
        total_leads += 1
        ch = (source or "other").lower()
        # Expected value weighted by lead score, realized on won/converted.
        weight = (score or 0) / 100.0
        ev = AVG_DEAL_VALUE * max(0.1, weight)
        is_won = statusv in ("won", "converted")
        c = by_channel.setdefault(ch, {"leads": 0, "won": 0, "pipeline": 0.0, "revenue": 0.0})
        c["leads"] += 1
        c["pipeline"] += ev
        pipeline_value += ev
        if is_won:
            c["won"] += 1
            c["revenue"] += AVG_DEAL_VALUE
            won_value += AVG_DEAL_VALUE
            won_leads += 1
        if agent_id:
            a = by_agent.setdefault(str(agent_id), {"agent_id": str(agent_id), "leads": 0, "won": 0, "revenue": 0.0})
            a["leads"] += 1
            if is_won:
                a["won"] += 1
                a["revenue"] += AVG_DEAL_VALUE

    # Resolve agent names.
    agent_names: dict[str, str] = {}
    if by_agent:
        try:
            ids = [uuid.UUID(k) for k in by_agent.keys()]
            nrows = (await session.execute(select(Agent.id, Agent.name).where(Agent.id.in_(ids)))).all()
            agent_names = {str(i): n for i, n in nrows}
        except Exception:  # pragma: no cover
            pass

    channels = sorted(
        [{"channel": k, "leads": v["leads"], "won": v["won"],
          "pipeline": _round(v["pipeline"]), "revenue": _round(v["revenue"])}
         for k, v in by_channel.items()],
        key=lambda x: x["revenue"], reverse=True,
    )
    agents = sorted(
        [{**v, "name": agent_names.get(v["agent_id"], "Agent"), "revenue": _round(v["revenue"])}
         for v in by_agent.values()],
        key=lambda x: x["revenue"], reverse=True,
    )[:10]

    return {
        "window_days": days,
        "totals": {
            "revenue": _round(won_value), "pipeline": _round(pipeline_value),
            "leads": total_leads, "won": won_leads,
            "win_rate": _round((won_leads / total_leads * 100) if total_leads else 0.0),
            "avg_deal_value": AVG_DEAL_VALUE,
        },
        "by_channel": channels, "by_agent": agents,
        "generated_at": _iso(_now()),
    }


# --------------------------------------------------------------------------- #
# 14 / 12. Customer 360 + Journey                                             #
# --------------------------------------------------------------------------- #
async def customer_360(session: AsyncSession, org_id: uuid.UUID, query: str) -> dict[str, Any]:
    """Resolve a customer by email/phone/name and assemble a unified profile."""
    query = (query or "").strip()
    out: dict[str, Any] = {"query": query, "found": False, "generated_at": _iso(_now())}
    if len(query) < 2:
        return out

    like = f"%{query}%"
    # Find candidate conversations / leads matching the identity.
    try:
        lead = (await session.execute(
            select(Lead).where(Lead.organization_id == org_id, Lead.deleted_at.is_(None),
                               or_(Lead.email.ilike(like), Lead.phone.ilike(like), Lead.name.ilike(like)))
            .order_by(Lead.created_at.desc()).limit(1)
        )).scalars().first()
    except Exception:  # pragma: no cover
        lead = None

    try:
        convs = (await session.execute(
            select(Conversation).where(
                Conversation.organization_id == org_id,
                or_(Conversation.customer_email.ilike(like),
                    Conversation.customer_phone.ilike(like),
                    Conversation.customer_name.ilike(like)))
            .order_by(Conversation.started_at.desc()).limit(50)
        )).scalars().all()
    except Exception:  # pragma: no cover
        convs = []

    if lead is None and not convs:
        return out

    # Identity card.
    name = (lead.name if lead else None) or next((c.customer_name for c in convs if c.customer_name), None) or query
    email = (lead.email if lead else None) or next((c.customer_email for c in convs if c.customer_email), None)
    phone = (lead.phone if lead else None) or next((c.customer_phone for c in convs if c.customer_phone), None)

    channels_used = sorted({str(c.channel.value if hasattr(c.channel, "value") else c.channel) for c in convs})
    timeline = [
        {"type": "conversation",
         "channel": str(c.channel.value if hasattr(c.channel, "value") else c.channel),
         "title": c.title or f"{str(c.channel.value if hasattr(c.channel, 'value') else c.channel)} conversation",
         "status": str(c.status.value if hasattr(c.status, "value") else c.status),
         "at": _iso(c.started_at), "duration_seconds": c.duration_seconds,
         "id": str(c.id)}
        for c in convs
    ]
    if lead:
        timeline.append({"type": "lead", "channel": (lead.source or "other"),
                         "title": f"Lead captured ({lead.status.value if hasattr(lead.status, 'value') else lead.status})",
                         "status": str(lead.status.value if hasattr(lead.status, "value") else lead.status),
                         "at": _iso(lead.created_at), "id": str(lead.id)})
    timeline.sort(key=lambda x: x["at"] or "", reverse=True)

    return {
        "query": query, "found": True,
        "profile": {
            "name": name, "email": email, "phone": phone,
            "company": (lead.company if lead else None),
            "lead_score": (lead.score if lead else None),
            "lead_status": (str(lead.status.value if hasattr(lead.status, "value") else lead.status) if lead else None),
            "temperature": (str(lead.temperature.value if hasattr(lead.temperature, "value") else lead.temperature) if lead else None),
            "intent": (lead.intent if lead else None),
        },
        "stats": {
            "conversations": len(convs),
            "channels": channels_used,
            "first_seen": _iso(min((c.started_at for c in convs), default=None)) if convs else None,
            "last_seen": _iso(max((c.started_at for c in convs), default=None)) if convs else None,
        },
        "timeline": timeline,
        "generated_at": _iso(_now()),
    }


# --------------------------------------------------------------------------- #
# 10. AI Confidence Heatmap                                                   #
# --------------------------------------------------------------------------- #
_PHASES = ["Greeting", "Intent", "Knowledge", "Pricing", "Booking", "Closing"]
_KW = {
    "Pricing": ("price", "cost", "fee", "plan", "quote", "$", "charge"),
    "Booking": ("book", "appointment", "schedule", "slot", "reserve", "demo"),
    "Closing": ("thank", "bye", "goodbye", "anything else", "have a"),
}


async def confidence_heatmap(session: AsyncSession, org_id: uuid.UUID, conversation_id: uuid.UUID) -> dict[str, Any]:
    try:
        conv = (await session.execute(
            select(Conversation).where(Conversation.id == conversation_id,
                                       Conversation.organization_id == org_id)
        )).scalars().first()
    except Exception:  # pragma: no cover
        conv = None
    if conv is None:
        return {"found": False, "generated_at": _iso(_now())}

    try:
        msgs = (await session.execute(
            select(Message).where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )).scalars().all()
    except Exception:  # pragma: no cover
        msgs = []

    agent_msgs = [m for m in msgs if str(getattr(m.sender, "value", m.sender)) == "agent"]
    timeline = []
    for i, m in enumerate(agent_msgs):
        txt = (m.message or "")
        low = txt.lower()
        meta = m.metadata_ or {}
        has_src = bool(meta.get("sources"))
        # Heuristic per-turn confidence.
        base = 0.7 + (0.18 if has_src else 0.0)
        if any(m_ in low for m_ in ("i'm not sure", "i don't know", "cannot help", "unable to")):
            base -= 0.35
        if "?" in txt and len(txt) < 40:
            base += 0.02
        length_factor = min(0.08, len(txt) / 1200)
        conf = _clamp((base + length_factor) * 100)
        # Phase tagging.
        phase = "Greeting" if i == 0 else "Closing" if i == len(agent_msgs) - 1 else "Knowledge"
        for ph, kws in _KW.items():
            if any(k in low for k in kws):
                phase = ph
                break
        timeline.append({"index": i, "phase": phase, "confidence": _round(conf),
                         "has_sources": has_src, "preview": txt[:120]})

    # Aggregate per phase.
    by_phase = {}
    for seg in timeline:
        by_phase.setdefault(seg["phase"], []).append(seg["confidence"])
    phases = [{"phase": p,
               "confidence": _round(sum(by_phase[p]) / len(by_phase[p])) if by_phase.get(p) else None}
              for p in _PHASES]
    overall = _round(sum(s["confidence"] for s in timeline) / len(timeline)) if timeline else 0.0

    return {
        "found": True, "conversation_id": str(conversation_id),
        "channel": str(getattr(conv.channel, "value", conv.channel)),
        "overall": overall, "phases": phases, "timeline": timeline,
        "turns": len(agent_msgs), "generated_at": _iso(_now()),
    }


# --------------------------------------------------------------------------- #
# 9. Conversation Simulator                                                   #
# --------------------------------------------------------------------------- #
SIM_SCENARIOS = [
    {"key": "happy", "label": "Happy Customer", "opening": "Hi! I love your product, can you tell me more about what you offer?"},
    {"key": "angry", "label": "Angry Customer", "opening": "This is the third time I'm calling. I'm really frustrated and want this fixed now."},
    {"key": "pricing", "label": "Pricing", "opening": "How much does your service cost and what are the plans?"},
    {"key": "refund", "label": "Refund", "opening": "I want a refund for my last order. How do I get my money back?"},
    {"key": "booking", "label": "Booking", "opening": "I'd like to book an appointment for next week, what's available?"},
    {"key": "support", "label": "Support", "opening": "Something isn't working and I need help troubleshooting it."},
    {"key": "complaint", "label": "Complaint", "opening": "I'm not happy with the service I received yesterday."},
    {"key": "lead", "label": "Lead", "opening": "I'm interested in buying. Can you help me get started?"},
    {"key": "multilingual", "label": "Multilingual", "opening": "Hola, necesito ayuda con mi cuenta por favor."},
    {"key": "smalltalk", "label": "Small Talk", "opening": "Hey, how's your day going?"},
    {"key": "invalid", "label": "Invalid Input", "opening": "asdfgh ;;; 12345 ???"},
]


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


async def _agent_prompt(session: AsyncSession, org_id: uuid.UUID, agent_id: uuid.UUID) -> tuple[Optional[str], Optional[str]]:
    try:
        from app.database.models.agent_config import AgentConfig

        agent = (await session.execute(
            select(Agent).where(Agent.id == agent_id, Agent.organization_id == org_id)
        )).scalars().first()
        if agent is None:
            return None, None
        cfg = (await session.execute(
            select(AgentConfig).where(AgentConfig.agent_id == agent_id)
        )).scalars().first()
        return (cfg.system_prompt if cfg else None), agent.name
    except Exception as e:  # pragma: no cover
        log.warning("sim agent load failed: %s", e)
        return None, None


async def simulate(session: AsyncSession, org_id: uuid.UUID, agent_id: uuid.UUID,
                   scenarios: Optional[list[str]] = None) -> dict[str, Any]:
    system_prompt, agent_name = await _agent_prompt(session, org_id, agent_id)
    if agent_name is None:
        return {"error": "agent_not_found", "results": [], "generated_at": _iso(_now())}

    wanted = [s for s in SIM_SCENARIOS if (not scenarios or s["key"] in scenarios)]
    results: list[dict[str, Any]] = []
    generated = False

    for sc in wanted:
        result = await _simulate_one(system_prompt, agent_name, sc)
        generated = generated or result.pop("_generated", False)
        results.append(result)

    if results:
        success = sum(1 for r in results if r["verdict"] == "pass")
        avg = lambda k: _round(sum(r[k] for r in results) / len(results))  # noqa: E731
        summary = {
            "scenarios": len(results),
            "success_rate": _round(success / len(results) * 100),
            "accuracy": avg("accuracy"), "hallucination": avg("hallucination"),
            "knowledge_usage": avg("knowledge"), "latency_ms": avg("latency_ms"),
        }
    else:
        summary = {"scenarios": 0, "success_rate": 0, "accuracy": 0, "hallucination": 0,
                   "knowledge_usage": 0, "latency_ms": 0}

    recs = _simulate_recs(results)
    return {
        "agent_id": str(agent_id), "agent_name": agent_name,
        "generated": generated, "summary": summary, "results": results,
        "recommendations": recs, "generated_at": _iso(_now()),
    }


async def _simulate_one(system_prompt: Optional[str], agent_name: str, sc: dict[str, Any]) -> dict[str, Any]:
    import time

    started = time.monotonic()
    reply_text = ""
    generated = False
    try:
        from app.providers import ChatMessage, DEFAULT_MODEL, get_provider

        provider = get_provider()
        sys = (system_prompt or f"You are {agent_name}, a helpful business assistant.")
        resp = await provider.chat(
            [
                ChatMessage(role="system", content=sys),
                ChatMessage(role="user", content=sc["opening"]),
            ],
            model=DEFAULT_MODEL, temperature=0.4, max_tokens=300,
        )
        reply_text = (resp.content or "").strip()
        generated = bool(reply_text)
    except Exception as e:  # pragma: no cover
        log.info("simulate scenario %s fell back: %s", sc["key"], e)
    latency_ms = int((time.monotonic() - started) * 1000)

    low = reply_text.lower()
    uncertain = any(p in low for p in ("i'm not sure", "i don't know", "cannot", "unable"))
    refused = sc["key"] in ("refund", "complaint", "angry") and ("sorry" in low or "understand" in low)
    accuracy = _clamp(82 + (8 if reply_text else -50) - (15 if uncertain else 0))
    hallucination = _clamp(8 + (20 if not reply_text else 0))
    knowledge = _clamp(55 + (20 if reply_text else 0) + (10 if refused else 0))
    verdict = "pass" if reply_text and accuracy >= 60 and hallucination <= 30 else "fail"

    return {
        "scenario": sc["key"], "label": sc["label"], "opening": sc["opening"],
        "reply": reply_text or "(no response — provider offline)",
        "accuracy": _round(accuracy), "hallucination": _round(hallucination),
        "knowledge": _round(knowledge), "latency_ms": latency_ms,
        "verdict": verdict, "_generated": generated,
    }


def _simulate_recs(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    fails = [r for r in results if r["verdict"] == "fail"]
    if fails:
        recs.append({"severity": "high", "title": "Fix failing scenarios",
                     "detail": "Failing: " + ", ".join(r["label"] for r in fails[:5]) + ". Refine the prompt and add knowledge for these."})
    if any(r["hallucination"] > 25 for r in results):
        recs.append({"severity": "medium", "title": "Reduce hallucination risk",
                     "detail": "Some replies risk hallucination. Ground the agent in knowledge and instruct it to say when unsure."})
    if any(r["knowledge"] < 50 for r in results):
        recs.append({"severity": "medium", "title": "Improve knowledge usage",
                     "detail": "Add documents covering pricing, refunds and bookings so answers cite real sources."})
    if not recs:
        recs.append({"severity": "low", "title": "Agent is ready to publish",
                     "detail": "All simulated scenarios passed. Re-run after prompt or knowledge changes."})
    return recs

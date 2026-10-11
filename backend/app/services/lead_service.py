"""Lead service — scoring heuristics + capture helper.

Shared by the dashboard ``/api/leads`` router and the public widget lead
endpoint so a captured contact always produces a first-class ``leads`` row
with a sensible score/temperature.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.lead import Lead, LeadStatus, LeadTemperature


# Intent keywords that signal buying interest → boost the score.
_HOT_KEYWORDS = (
    "quote", "quotation", "pricing", "price", "buy", "purchase", "demo",
    "trial", "book", "appointment", "schedule", "contract", "invoice",
    "subscribe", "upgrade", "enterprise", "sales", "talk to",
)
_WARM_KEYWORDS = (
    "interested", "info", "information", "details", "learn", "how much",
    "compare", "feature", "support", "help",
)


def score_lead(
    *,
    email: Optional[str],
    phone: Optional[str],
    company: Optional[str],
    intent: Optional[str],
    message: Optional[str],
) -> tuple[int, LeadTemperature]:
    """Deterministic 0-100 lead score + temperature.

    Completeness of contact details + buying-intent keywords drive the score.
    """
    score = 0
    if email:
        score += 30
    if phone:
        score += 25
    if company:
        score += 15

    blob = " ".join(filter(None, [intent or "", message or ""])).lower()
    if any(k in blob for k in _HOT_KEYWORDS):
        score += 30
    elif any(k in blob for k in _WARM_KEYWORDS):
        score += 12

    score = max(0, min(100, score))

    if score >= 70:
        temp = LeadTemperature.hot
    elif score >= 40:
        temp = LeadTemperature.warm
    else:
        temp = LeadTemperature.cold
    return score, temp


async def create_lead(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    agent_id: Optional[uuid.UUID] = None,
    widget_id: Optional[uuid.UUID] = None,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    intent: Optional[str] = None,
    message: Optional[str] = None,
    source: str = "widget",
    status: Optional[LeadStatus] = None,
    score: Optional[int] = None,
    temperature: Optional[LeadTemperature] = None,
) -> Lead:
    """Create + flush a Lead, auto-scoring when score is not supplied."""
    if score is None or temperature is None:
        auto_score, auto_temp = score_lead(
            email=email, phone=phone, company=company, intent=intent, message=message
        )
        score = auto_score if score is None else score
        temperature = auto_temp if temperature is None else temperature

    lead = Lead(
        organization_id=organization_id,
        project_id=project_id,
        conversation_id=conversation_id,
        agent_id=agent_id,
        widget_id=widget_id,
        name=(name or None),
        email=(email or None),
        phone=(phone or None),
        company=(company or None),
        intent=(intent or None),
        message=(message or None),
        source=source,
        status=status or LeadStatus.new,
        score=score,
        temperature=temperature,
    )
    session.add(lead)
    await session.flush()
    return lead


async def upsert_conversation_lead(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    conversation_id: Optional[uuid.UUID],
    project_id: Optional[uuid.UUID] = None,
    agent_id: Optional[uuid.UUID] = None,
    widget_id: Optional[uuid.UUID] = None,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    intent: Optional[str] = None,
    message: Optional[str] = None,
    source: str = "chat",
    status: Optional[LeadStatus] = None,
) -> Lead:
    """Create-or-update the single lead attached to a conversation.

    Every visitor who chats (even one "just checking" with no contact details)
    becomes a first-class lead, and their thread is the lead's source of truth.
    Deduped on ``conversation_id`` so a later lead-form submission enriches the
    same lead instead of creating a duplicate. Known values are never blanked
    out; the score only ever moves up as the visitor reveals more intent.
    """
    existing: Optional[Lead] = None
    if conversation_id is not None:
        existing = await session.scalar(
            select(Lead)
            .where(Lead.organization_id == organization_id)
            .where(Lead.conversation_id == conversation_id)
            .where(Lead.deleted_at.is_(None))
            .limit(1)
        )

    if existing is None:
        return await create_lead(
            session,
            organization_id=organization_id,
            project_id=project_id,
            conversation_id=conversation_id,
            agent_id=agent_id,
            widget_id=widget_id,
            name=name,
            email=email,
            phone=phone,
            company=company,
            intent=intent,
            message=message,
            source=source,
            status=status,
        )

    # Merge — fill blanks only, never overwrite a known value with None.
    if name and not existing.name:
        existing.name = name
    if email and not existing.email:
        existing.email = email
    if phone and not existing.phone:
        existing.phone = phone
    if company and not existing.company:
        existing.company = company
    if intent and not existing.intent:
        existing.intent = intent
    if message and not existing.message:
        existing.message = message
    # A lead-form submission is a stronger signal than a passive chat.
    if source == "widget" and existing.source != "widget":
        existing.source = source
    # Re-score with the merged data; only ever raise the score/temperature.
    new_score, new_temp = score_lead(
        email=existing.email,
        phone=existing.phone,
        company=existing.company,
        intent=existing.intent,
        message=message or existing.message,
    )
    if new_score >= existing.score:
        existing.score = new_score
        existing.temperature = new_temp
    if status is not None:
        existing.status = status
    await session.flush()
    return existing

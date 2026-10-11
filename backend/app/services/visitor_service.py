"""Cross-channel visitor identity & shared memory service.

Resolves and maintains :class:`VisitorProfile` records so one person is
recognised across every channel (website chat, WhatsApp/SMS, forms, api) and
the agent can be primed with what it already knows about them — no repeated
questions. All writes reassign new JSONB containers so SQLAlchemy reliably
detects the change (the columns are plain ``JSONB``, not ``MutableDict``).
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.conversation import Conversation
from app.database.models.visitor_profile import VisitorProfile

# Keep the rolling memory small so the prompt stays cheap and fast.
_MEMORY_CAP = 12
_DIGEST_MAX_CHARS = 900
_CONTEXT_VALUE_MAX = 300


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.strip().lower()
    return v if "@" in v and len(v) <= 255 else None


def normalize_phone(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = re.sub(r"[^\d+]", "", value.strip())
    return digits[:40] or None


def _clean_context(ctx: Optional[dict]) -> dict[str, Any]:
    if not isinstance(ctx, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in ctx.items():
        if v is None:
            continue
        out[str(k)[:60]] = str(v)[:_CONTEXT_VALUE_MAX]
    return out


async def _lookup_by_key(
    session: AsyncSession, organization_id: uuid.UUID, key: str
) -> Optional[VisitorProfile]:
    """Resolve a profile whose ``visitor_key`` is ``key`` OR which has folded
    ``key`` in as an alias."""
    return await session.scalar(
        select(VisitorProfile)
        .where(VisitorProfile.organization_id == organization_id)
        .where(
            or_(
                VisitorProfile.visitor_key == key,
                VisitorProfile.aliases.contains([key]),
            )
        )
        .order_by(VisitorProfile.first_seen_at.asc())
        .limit(1)
    )


async def find_by_identity(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    email: Optional[str] = None,
    phone: Optional[str] = None,
) -> Optional[VisitorProfile]:
    """Resolve the durable identity for an org by a known email/phone — this is
    what lets a person identified in chat be recognised when they later call,
    and vice-versa. Returns the oldest (most-established) match."""
    email = normalize_email(email)
    phone = normalize_phone(phone)
    conds = []
    if email:
        conds.append(VisitorProfile.email == email)
    if phone:
        conds.append(VisitorProfile.phone == phone)
    if not conds:
        return None
    return await session.scalar(
        select(VisitorProfile)
        .where(VisitorProfile.organization_id == organization_id)
        .where(or_(*conds))
        .order_by(VisitorProfile.first_seen_at.asc())
        .limit(1)
    )


async def _merge_profiles(
    session: AsyncSession, *, primary: VisitorProfile, secondary: VisitorProfile
) -> VisitorProfile:
    """Fold ``secondary`` into ``primary`` (the durable identity) so a single
    person never ends up as two profiles. Memory, context, channels and
    conversations all move onto ``primary``; ``secondary`` is deleted and its
    key(s) recorded as aliases."""
    if primary.id == secondary.id:
        return primary

    primary.name = primary.name or secondary.name
    primary.email = primary.email or secondary.email
    primary.phone = primary.phone or secondary.phone
    primary.lead_score = primary.lead_score if primary.lead_score is not None else secondary.lead_score
    primary.lead_status = primary.lead_status or secondary.lead_status

    # secondary's context fills only gaps — primary (the identity) wins.
    primary.shared_context = {
        **(secondary.shared_context or {}),
        **(primary.shared_context or {}),
    }

    used = list(primary.channels_used or [])
    for c in secondary.channels_used or []:
        if c not in used:
            used.append(c)
    primary.channels_used = used

    merged_mem = list(secondary.memory or []) + list(primary.memory or [])
    merged_mem.sort(key=lambda m: m.get("at") or "")
    primary.memory = merged_mem[-_MEMORY_CAP:]

    aliases = list(primary.aliases or [])
    for a in [secondary.visitor_key, *(secondary.aliases or [])]:
        if a and a != primary.visitor_key and a not in aliases:
            aliases.append(a)
    primary.aliases = aliases

    primary.conversation_count = (primary.conversation_count or 0) + (
        secondary.conversation_count or 0
    )
    if secondary.last_conversation_id and not primary.last_conversation_id:
        primary.last_conversation_id = secondary.last_conversation_id

    # Re-point any conversations that referenced the secondary profile.
    await session.execute(
        update(Conversation)
        .where(Conversation.visitor_profile_id == secondary.id)
        .values(visitor_profile_id=primary.id)
    )
    await session.delete(secondary)
    await session.flush()
    primary.last_seen_at = now_utc()
    return primary


def _add_alias(profile: VisitorProfile, key: str) -> None:
    if not key or key == profile.visitor_key:
        return
    aliases = list(profile.aliases or [])
    if key not in aliases:
        profile.aliases = aliases + [key]


async def upsert_profile(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    visitor_key: str,
    channel: Optional[str] = None,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    context: Optional[dict] = None,
) -> VisitorProfile:
    """Find-or-create the ONE profile for this person and fold in any new
    identity / context we just learned.

    Resolution is cross-channel: we match on ``visitor_key`` (or an alias) AND
    on any supplied email/phone identity. When both a channel-local profile and
    a durable identity profile exist they are merged into a single record, so
    the agent shares memory whether the visitor arrives by chat, phone or form.
    Returns the (flushed) profile.
    """
    visitor_key = (visitor_key or "").strip()[:160]
    if not visitor_key:
        visitor_key = f"anon_{uuid.uuid4().hex[:16]}"

    email = normalize_email(email)
    phone = normalize_phone(phone)
    name = (name or "").strip()[:160] or None
    new_ctx = _clean_context(context)

    by_key = await _lookup_by_key(session, organization_id, visitor_key)
    by_identity = await find_by_identity(
        session, organization_id, email=email, phone=phone
    )

    profile: Optional[VisitorProfile]
    if by_key is not None and by_identity is not None and by_key.id != by_identity.id:
        # Same human reached us two ways — collapse into the durable identity.
        profile = await _merge_profiles(
            session, primary=by_identity, secondary=by_key
        )
        _add_alias(profile, visitor_key)
    elif by_identity is not None:
        profile = by_identity
        _add_alias(profile, visitor_key)
    else:
        profile = by_key

    if profile is None:
        profile = VisitorProfile(
            organization_id=organization_id,
            visitor_key=visitor_key,
            name=name,
            email=email,
            phone=phone,
            shared_context=new_ctx,
            channels_used=[channel] if channel else [],
            aliases=[],
            memory=[],
            first_seen_at=now_utc(),
            last_seen_at=now_utc(),
        )
        session.add(profile)
        await session.flush()
        return profile

    # Merge — never blank out a known value with a missing one.
    profile.name = profile.name or name
    profile.email = profile.email or email
    profile.phone = profile.phone or phone
    if new_ctx:
        profile.shared_context = {**(profile.shared_context or {}), **new_ctx}
    if channel:
        used = list(profile.channels_used or [])
        if channel not in used:
            profile.channels_used = used + [channel]
    profile.last_seen_at = now_utc()
    await session.flush()
    return profile


def append_memory(
    profile: VisitorProfile,
    *,
    channel: str,
    role: str,
    text: str,
) -> None:
    """Add one capped highlight to the visitor's rolling cross-channel memory."""
    text = (text or "").strip()
    if not text:
        return
    entry = {
        "channel": channel,
        "role": role,
        "text": text[:400],
        "at": now_utc().isoformat(),
    }
    memory = list(profile.memory or [])
    memory.append(entry)
    profile.memory = memory[-_MEMORY_CAP:]


def link_conversation(
    profile: VisitorProfile, conversation: Conversation, *, channel: str
) -> None:
    """Attach a conversation to the profile and update rollups."""
    if conversation.visitor_profile_id != profile.id:
        conversation.visitor_profile_id = profile.id
        profile.conversation_count = (profile.conversation_count or 0) + 1
    profile.last_conversation_id = conversation.id
    profile.last_channel = channel
    profile.last_seen_at = now_utc()


def build_memory_digest(
    profile: VisitorProfile, *, current_channel: Optional[str] = None
) -> Optional[str]:
    """Render a compact, prompt-injectable block describing what we already
    know about this visitor. Returns ``None`` when there's nothing useful."""
    lines: list[str] = []

    identity: list[str] = []
    if profile.name:
        identity.append(f"name: {profile.name}")
    if profile.email:
        identity.append(f"email: {profile.email}")
    if profile.phone:
        identity.append(f"phone: {profile.phone}")
    ctx = profile.shared_context or {}
    for key in ("company", "plan", "language", "userId"):
        if ctx.get(key):
            identity.append(f"{key}: {ctx[key]}")
    if identity:
        lines.append("Known visitor — " + ", ".join(identity) + ".")

    channels = [c for c in (profile.channels_used or []) if c != current_channel]
    if channels:
        lines.append("Previously talked via: " + ", ".join(channels) + ".")

    recent = (profile.memory or [])[-6:]
    if recent:
        lines.append("Recent context from earlier conversations:")
        for m in recent:
            who = "Them" if m.get("role") in ("user", "customer") else "You"
            ch = m.get("channel", "?")
            lines.append(f"- ({ch}) {who}: {m.get('text', '')}")

    if not lines:
        return None

    digest = "\n".join(lines)
    if len(digest) > _DIGEST_MAX_CHARS:
        digest = digest[:_DIGEST_MAX_CHARS].rsplit("\n", 1)[0]
    return digest

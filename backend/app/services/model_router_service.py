"""AI model router (Phase 12, Module 13).

Resolves the *effective* model for a request given (a) the org's routing
policy, (b) the plan's entitlements, and (c) catalogue availability —
falling back gracefully so inference never dies on a bad/disabled model
id. Also powers the management view used by the dashboard.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_catalogue import (
    DEFAULT_ROUTING_STRATEGY,
    MODEL_CATALOGUE,
    ROUTING_STRATEGIES,
    SAFE_DEFAULT_MODEL,
    entitled_models,
    get_model,
    is_entitled,
    order_by_strategy,
)
from app.database.models.ai_model_policy import AIModelPolicy
from app.database.models.conversation import Conversation
from app.database.models.message import Message
from app.services import billing_service


def _settings(policy: Optional[AIModelPolicy]) -> dict:
    return dict(policy.settings or {}) if policy else {}


def _routing_strategy(policy: Optional[AIModelPolicy]) -> str:
    strat = str(_settings(policy).get("routing_strategy") or DEFAULT_ROUTING_STRATEGY).lower()
    return strat if strat in ROUTING_STRATEGIES else DEFAULT_ROUTING_STRATEGY


def _monthly_budget(policy: Optional[AIModelPolicy]) -> Optional[float]:
    val = _settings(policy).get("monthly_budget_usd")
    try:
        return float(val) if val not in (None, "") and float(val) > 0 else None
    except (TypeError, ValueError):
        return None


def _max_latency(policy: Optional[AIModelPolicy]) -> Optional[int]:
    val = _settings(policy).get("max_latency_ms")
    try:
        return int(val) if val not in (None, "") and int(val) > 0 else None
    except (TypeError, ValueError):
        return None


def _retrieval(policy: Optional[AIModelPolicy]) -> dict:
    """Effective hybrid-retrieval config (with safe defaults)."""
    from app.services import reranker as rerank_mod

    raw = _settings(policy).get("retrieval") or {}
    provider = str(raw.get("reranker") or rerank_mod.DEFAULT_PROVIDER).lower()
    if provider not in rerank_mod.VALID_PROVIDERS:
        provider = rerank_mod.DEFAULT_PROVIDER
    try:
        top_n = int(raw.get("rerank_top_n") or 24)
    except (TypeError, ValueError):
        top_n = 24
    return {
        "hybrid_enabled": bool(raw.get("hybrid_enabled", True)),
        "reranker": provider,
        "rerank_top_n": max(4, min(top_n, 60)),
    }


async def retrieval_config(
    session: AsyncSession, organization_id: uuid.UUID
) -> dict:
    """The org's hybrid-retrieval / reranker settings."""
    return _retrieval(await get_policy(session, organization_id))



async def current_month_spend(
    session: AsyncSession, organization_id: uuid.UUID
) -> float:
    """Sum the org's stored per-message AI cost for the current calendar month."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    cost_col = cast(Message.metadata_["cost_usd"].astext, Float)
    total = await session.scalar(
        select(func.coalesce(func.sum(cost_col), 0.0))
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.organization_id == organization_id)
        .where(Message.created_at >= month_start)
    )
    return round(float(total or 0.0), 6)


async def _plan_code(session: AsyncSession, organization_id: uuid.UUID) -> str:
    sub = await billing_service.get_or_create_subscription(session, organization_id)
    code = getattr(sub.plan.code, "value", sub.plan.code)
    return str(code)


async def get_policy(
    session: AsyncSession, organization_id: uuid.UUID
) -> Optional[AIModelPolicy]:
    return await session.scalar(
        select(AIModelPolicy).where(
            AIModelPolicy.organization_id == organization_id
        )
    )


async def get_or_create_policy(
    session: AsyncSession, organization_id: uuid.UUID
) -> AIModelPolicy:
    policy = await get_policy(session, organization_id)
    if policy is not None:
        return policy
    policy = AIModelPolicy(
        organization_id=organization_id,
        default_model=SAFE_DEFAULT_MODEL,
        fallback_models=[],
        disabled_models=[],
    )
    session.add(policy)
    await session.commit()
    await session.refresh(policy)
    return policy


def _usable(model_id: str, plan_code: str, disabled: list[str]) -> bool:
    model = get_model(model_id)
    if model is None:
        return False
    if model_id in (disabled or []):
        return False
    return is_entitled(model, plan_code)


async def resolve(
    session: AsyncSession,
    organization_id: uuid.UUID,
    requested_model: Optional[str] = None,
) -> str:
    """Pick the effective model id.

    Order of preference: the requested model (if usable) → policy default
    → policy fallbacks → entitled catalogue (ordered by the org's routing
    strategy) → SAFE_DEFAULT. A model slower than the org's latency limit
    is skipped, and if the org is over its monthly budget every request is
    routed to the cheapest usable model.
    """
    chain = await ordered_chain(session, organization_id, requested_model)
    return chain[0] if chain else SAFE_DEFAULT_MODEL


async def ordered_chain(
    session: AsyncSession,
    organization_id: uuid.UUID,
    requested_model: Optional[str] = None,
) -> list[str]:
    """The full ordered list of usable model ids for a request.

    The first entry is the model that *should* answer; the rest are the
    runtime fallback chain to try in order if a provider call fails.
    """
    plan_code = await _plan_code(session, organization_id)
    policy = await get_policy(session, organization_id)
    disabled = list(policy.disabled_models) if policy else []
    strategy = _routing_strategy(policy)
    max_latency = _max_latency(policy)

    # Over budget → cheapest-first regardless of the configured strategy.
    over_budget = False
    budget = _monthly_budget(policy)
    if budget is not None:
        spend = await current_month_spend(session, organization_id)
        over_budget = spend >= budget

    candidates: list[str] = []
    if not over_budget and requested_model:
        candidates.append(requested_model)
    if policy and not over_budget:
        candidates.append(policy.default_model)
        candidates.extend(policy.fallback_models or [])

    effective_strategy = "cheapest" if over_budget else strategy
    for m in order_by_strategy(entitled_models(plan_code), effective_strategy):
        candidates.append(m["id"])
    candidates.append(SAFE_DEFAULT_MODEL)

    chain: list[str] = []
    seen: set[str] = set()
    for cid in candidates:
        if not cid or cid in seen:
            continue
        seen.add(cid)
        if not _usable(cid, plan_code, disabled):
            continue
        if max_latency is not None:
            model = get_model(cid)
            if model and int(model.get("typical_latency_ms", 0)) > max_latency:
                # Only skip on latency if a faster option remains; otherwise
                # keep it so the request still resolves to something.
                continue
        chain.append(cid)

    if not chain:
        chain = [SAFE_DEFAULT_MODEL]
    return chain



async def router_view(
    session: AsyncSession, organization_id: uuid.UUID
) -> dict:
    """Catalogue annotated with entitlement/enabled state + current policy."""
    plan_code = await _plan_code(session, organization_id)
    policy = await get_or_create_policy(session, organization_id)
    disabled = set(policy.disabled_models or [])

    models = []
    for m in MODEL_CATALOGUE:
        entitled = is_entitled(m, plan_code)
        models.append({
            **m,
            "entitled": entitled,
            "enabled": entitled and m["id"] not in disabled,
            "disabled_by_org": m["id"] in disabled,
        })

    budget = _monthly_budget(policy)
    spend = await current_month_spend(session, organization_id)
    return {
        "plan_code": plan_code,
        "default_model": policy.default_model,
        "fallback_models": list(policy.fallback_models or []),
        "disabled_models": list(policy.disabled_models or []),
        "routing_strategy": _routing_strategy(policy),
        "monthly_budget_usd": budget,
        "max_latency_ms": _max_latency(policy),
        "current_month_spend_usd": spend,
        "budget_exceeded": budget is not None and spend >= budget,
        "retrieval": _retrieval(policy),
        "models": models,
    }


async def update_policy(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    default_model: str,
    fallback_models: list[str],
    disabled_models: list[str],
    routing_strategy: Optional[str] = None,
    monthly_budget_usd: Optional[float] = None,
    max_latency_ms: Optional[int] = None,
    hybrid_enabled: Optional[bool] = None,
    reranker: Optional[str] = None,
) -> AIModelPolicy:
    """Validate against entitlements and persist the org's routing policy."""
    from app.services import reranker as rerank_mod

    plan_code = await _plan_code(session, organization_id)
    entitled_ids = {m["id"] for m in entitled_models(plan_code)}

    if get_model(default_model) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown model '{default_model}'.",
        )
    if default_model not in entitled_ids:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"'{default_model}' isn't available on your current plan.",
        )
    if default_model in (disabled_models or []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The default model can't also be disabled.",
        )
    if routing_strategy is not None and routing_strategy not in ROUTING_STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown routing strategy '{routing_strategy}'.",
        )
    if reranker is not None and reranker.lower() not in rerank_mod.VALID_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown reranker '{reranker}'.",
        )

    # Keep only known, entitled fallbacks (preserve order, drop default dupes).
    clean_fallbacks: list[str] = []
    for fid in fallback_models or []:
        if (
            fid != default_model
            and fid in entitled_ids
            and fid not in clean_fallbacks
            and fid not in (disabled_models or [])
        ):
            clean_fallbacks.append(fid)

    # Disabled list: keep only known model ids.
    clean_disabled = [
        d for d in (disabled_models or [])
        if get_model(d) is not None and d != default_model
    ]

    policy = await get_or_create_policy(session, organization_id)
    policy.default_model = default_model
    policy.fallback_models = clean_fallbacks
    policy.disabled_models = clean_disabled

    settings = dict(policy.settings or {})
    if routing_strategy is not None:
        settings["routing_strategy"] = routing_strategy
    # ``monthly_budget_usd`` / ``max_latency_ms``: a value of 0 or None clears.
    budget = None
    try:
        budget = float(monthly_budget_usd) if monthly_budget_usd not in (None, "") else None
    except (TypeError, ValueError):
        budget = None
    settings["monthly_budget_usd"] = budget if budget and budget > 0 else None
    latency = None
    try:
        latency = int(max_latency_ms) if max_latency_ms not in (None, "") else None
    except (TypeError, ValueError):
        latency = None
    settings["max_latency_ms"] = latency if latency and latency > 0 else None

    # hybrid-retrieval / reranker config
    retrieval = dict(settings.get("retrieval") or {})
    if hybrid_enabled is not None:
        retrieval["hybrid_enabled"] = bool(hybrid_enabled)
    if reranker is not None:
        retrieval["reranker"] = reranker.lower()
    if retrieval:
        settings["retrieval"] = retrieval
    policy.settings = settings

    await session.commit()
    await session.refresh(policy)
    return policy

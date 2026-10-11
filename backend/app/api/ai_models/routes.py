"""Phase 12 Module 13 — AI model router management API.

* ``GET  /api/ai/models``          — catalogue + entitlement + policy.
* ``PUT  /api/ai/models/policy``   — set default / fallbacks / disabled.
* ``POST /api/ai/models/resolve``  — preview the router's decision.

Reading the catalogue requires ``settings.read``; changing the policy
requires ``settings.manage``.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission
from app.database.session import get_db
from app.middleware.org_context import (
    OrgContext,
    get_current_organization,
    require_permission,
)
from app.schemas.ai_models import (
    ModelPolicyUpdate,
    ModelRouterView,
    ResolveRequest,
    ResolveResponse,
)
from app.services import model_router_service
from app.services.audit import audit

router = APIRouter(tags=["ai-models"])


@router.get("/api/ai/models", response_model=ModelRouterView)
async def get_models(
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_READ)),
    session: AsyncSession = Depends(get_db),
) -> ModelRouterView:
    view = await model_router_service.router_view(session, ctx.organization_id)
    return ModelRouterView(**view)


@router.put("/api/ai/models/policy", response_model=ModelRouterView)
async def update_policy(
    payload: ModelPolicyUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> ModelRouterView:
    await model_router_service.update_policy(
        session,
        ctx.organization_id,
        default_model=payload.default_model,
        fallback_models=payload.fallback_models,
        disabled_models=payload.disabled_models,
        routing_strategy=payload.routing_strategy,
        monthly_budget_usd=payload.monthly_budget_usd,
        max_latency_ms=payload.max_latency_ms,
        hybrid_enabled=payload.hybrid_enabled,
        reranker=payload.reranker,
    )
    audit(
        "update",
        resource="ai_model_policy",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={
            "default_model": payload.default_model,
            "fallback_models": payload.fallback_models,
            "disabled_models": payload.disabled_models,
            "routing_strategy": payload.routing_strategy,
            "monthly_budget_usd": payload.monthly_budget_usd,
            "max_latency_ms": payload.max_latency_ms,
            "hybrid_enabled": payload.hybrid_enabled,
            "reranker": payload.reranker,
        },
    )
    view = await model_router_service.router_view(session, ctx.organization_id)
    return ModelRouterView(**view)


@router.post("/api/ai/models/resolve", response_model=ResolveResponse)
async def resolve_model(
    payload: ResolveRequest,
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_READ)),
    session: AsyncSession = Depends(get_db),
) -> ResolveResponse:
    resolved = await model_router_service.resolve(
        session, ctx.organization_id, payload.requested_model
    )
    return ResolveResponse(
        requested_model=payload.requested_model, resolved_model=resolved
    )


# ─────────────────────── Clarifying questions (agent builder) ───────────────────────
#
# After a user points the builder at their knowledge, the assistant proposes a
# short set of clarifying questions — Claude-Opus style: each question offers
# selectable option chips, and a final free-text prompt captures anything else.
# The answers are folded into the agent's system prompt by the frontend.

class ClarifyRequest(BaseModel):
    goal_id: Optional[str] = None
    goal_type: Optional[str] = None  # chat | whatsapp
    goal_title: Optional[str] = None
    source_kind: Optional[str] = None  # website | upload | text | integration | skip
    knowledge_base_id: Optional[str] = None


class ClarifyOption(BaseModel):
    id: str
    label: str


class ClarifyQuestion(BaseModel):
    id: str
    question: str
    type: Literal["single", "multi"] = "single"
    options: List[ClarifyOption] = Field(default_factory=list)
    optional: bool = False


class ClarifyResponse(BaseModel):
    intro: str
    questions: List[ClarifyQuestion]
    final_label: str
    final_placeholder: str


def _opt(label: str) -> ClarifyOption:
    slug = "".join(c if c.isalnum() else "_" for c in label.lower()).strip("_")
    return ClarifyOption(id=slug or "opt", label=label)


def _q(qid: str, question: str, labels: List[str], qtype: str = "single", optional: bool = False) -> ClarifyQuestion:
    return ClarifyQuestion(
        id=qid,
        question=question,
        type=qtype,  # type: ignore[arg-type]
        options=[_opt(l) for l in labels],
        optional=optional,
    )


def _build_clarifying_questions(req: ClarifyRequest) -> List[ClarifyQuestion]:
    goal = (req.goal_id or "").lower()
    questions: List[ClarifyQuestion] = [
        _q(
            "unknown_answer",
            "When your assistant isn't sure of an answer, what should it do?",
            [
                "Offer to connect to a human",
                "Ask for an email to follow up",
                "Say it's unsure and suggest related topics",
                "Give its best-effort answer anyway",
            ],
        ),
        _q(
            "priorities",
            "What should it prioritise in its replies?",
            [
                "Speed & brevity",
                "Step-by-step detail",
                "Citing the source",
                "Empathy & reassurance",
            ],
            qtype="multi",
        ),
    ]

    if goal == "sales":
        questions.append(
            _q(
                "lead_intent",
                "How proactively should it pursue leads?",
                ["Only when explicitly asked", "Capture an email when interest shows", "Always nudge toward a demo"],
            )
        )
    elif goal == "support":
        questions.append(
            _q(
                "frustration",
                "How should it handle a frustrated customer?",
                ["Apologise and escalate fast", "Stay calm and troubleshoot", "Offer goodwill options"],
            )
        )
    elif goal == "whatsapp":
        questions.append(
            _q(
                "message_style",
                "What WhatsApp style fits best?",
                ["Short, snappy texts", "Friendly with emoji", "Formal and precise"],
            )
        )
    else:
        questions.append(
            _q(
                "languages",
                "Which languages should it handle?",
                ["English", "Hindi", "Spanish", "Auto-detect the visitor's language"],
                qtype="multi",
            )
        )

    questions.append(
        _q(
            "avoid",
            "Are there topics it must avoid?",
            [
                "Pricing negotiations",
                "Legal advice",
                "Medical advice",
                "Competitor comparisons",
                "Nothing off-limits",
            ],
            qtype="multi",
            optional=True,
        )
    )
    return questions


@router.post("/api/ai/clarify", response_model=ClarifyResponse)
async def clarify_agent(
    payload: ClarifyRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> ClarifyResponse:
    """Propose clarifying questions to refine an agent before it goes live."""
    title = payload.goal_title or "your assistant"
    intro = (
        f"I've reviewed what {title} will learn from. A few quick questions will help "
        "me tune how it responds — pick the options that fit, then add anything else below."
    )
    return ClarifyResponse(
        intro=intro,
        questions=_build_clarifying_questions(payload),
        final_label="Anything specific it must always — or never — say?",
        final_placeholder="e.g. Always greet by name. Never promise refunds. Mention our 30-day trial when relevant.",
    )

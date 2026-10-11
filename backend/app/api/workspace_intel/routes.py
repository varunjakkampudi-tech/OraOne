"""Workspace-intelligence endpoints (org-scoped).

Exposes the higher-order analytics / AI tooling computed from a tenant's own
data: optimization score, knowledge coverage, revenue attribution, customer
360, confidence heatmap and the conversation simulator. All endpoints are
organization-scoped (RLS) and audit-logged.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.services import workspace_intelligence as wi
from app.services.audit import audit

router = APIRouter(prefix="/api/workspace", tags=["workspace-intelligence"])


@router.get("/optimization-score", summary="AI optimization score for the workspace")
async def get_optimization_score(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    data = await wi.optimization_score(session, ctx.organization_id)
    audit("read", resource="optimization_score",
          organization_id=str(ctx.organization_id), user_id=str(ctx.user_id),
          meta={"overall": data.get("overall")})
    return data


@router.get("/knowledge-coverage", summary="Knowledge base coverage analysis")
async def get_knowledge_coverage(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    data = await wi.knowledge_coverage(session, ctx.organization_id)
    audit("read", resource="knowledge_coverage",
          organization_id=str(ctx.organization_id), user_id=str(ctx.user_id),
          meta={"coverage": data.get("coverage")})
    return data


@router.get("/revenue-attribution", summary="Revenue attribution by channel & agent")
async def get_revenue_attribution(
    days: int = Query(90, ge=7, le=365),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    data = await wi.revenue_attribution(session, ctx.organization_id, days=days)
    audit("read", resource="revenue_attribution",
          organization_id=str(ctx.organization_id), user_id=str(ctx.user_id),
          meta={"days": days})
    return data


@router.get("/customer-360", summary="Unified customer profile & journey")
async def get_customer_360(
    q: str = Query(..., min_length=2, description="Email, phone or name"),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    data = await wi.customer_360(session, ctx.organization_id, q)
    audit("read", resource="customer_360",
          organization_id=str(ctx.organization_id), user_id=str(ctx.user_id),
          meta={"found": data.get("found")})
    return data


@router.get("/confidence-heatmap/{conversation_id}", summary="Per-turn AI confidence heatmap")
async def get_confidence_heatmap(
    conversation_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    data = await wi.confidence_heatmap(session, ctx.organization_id, conversation_id)
    audit("read", resource="confidence_heatmap",
          organization_id=str(ctx.organization_id), user_id=str(ctx.user_id),
          meta={"conversation_id": str(conversation_id)})
    return data


class SimulateRequest(BaseModel):
    agent_id: uuid.UUID
    scenarios: Optional[list[str]] = Field(default=None, description="Scenario keys; omit for all")


@router.get("/simulator/scenarios", summary="Available simulator scenarios")
async def list_sim_scenarios(
    ctx: OrgContext = Depends(get_current_organization),
) -> dict:
    return {"scenarios": [{"key": s["key"], "label": s["label"]} for s in wi.SIM_SCENARIOS]}


@router.post("/simulator/run", summary="Run the conversation simulator against an agent")
async def run_simulator(
    payload: SimulateRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    data = await wi.simulate(session, ctx.organization_id, payload.agent_id, payload.scenarios)
    audit("create", resource="conversation_simulation",
          organization_id=str(ctx.organization_id), user_id=str(ctx.user_id),
          meta={"agent_id": str(payload.agent_id),
                "success_rate": data.get("summary", {}).get("success_rate")})
    return data

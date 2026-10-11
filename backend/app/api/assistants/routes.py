"""Bonus AI assistants API.

A single, thin router over :mod:`app.services.assistants`. Every assistant
shares the same provider stack and returns a structured JSON result. Endpoints
are organization-scoped and audit-logged.

* ``GET  /api/assistants``            — list available assistants
* ``POST /api/assistants/{kind}/run`` — run one assistant with a free-form input
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.middleware.org_context import OrgContext, get_current_organization
from app.services import assistants
from app.services.audit import audit

router = APIRouter(prefix="/api/assistants", tags=["assistants"])


class AssistantRunIn(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


class AssistantRunOut(BaseModel):
    kind: str
    result: dict[str, Any]
    generated: bool


@router.get("")
async def list_assistants(
    _ctx: OrgContext = Depends(get_current_organization),
) -> list[dict[str, str]]:
    return assistants.catalog()


@router.post("/{kind}/run", response_model=AssistantRunOut)
async def run_assistant(
    kind: str,
    payload: AssistantRunIn,
    ctx: OrgContext = Depends(get_current_organization),
) -> AssistantRunOut:
    try:
        out = await assistants.run(kind, payload.input or {})
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown assistant.") from e

    audit(
        "run", resource="assistant", resource_id=kind,
        organization_id=str(ctx.organization_id), user_id=str(ctx.user_id),
        meta={"generated": out["generated"]},
    )
    return AssistantRunOut(kind=kind, result=out["result"], generated=out["generated"])

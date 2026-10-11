"""AI model router schemas (Phase 12, Module 13)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    id: str
    label: str
    provider: str
    family: str
    tier: str
    context_window: int
    input_per_1k: float
    output_per_1k: float
    typical_latency_ms: Optional[int] = None
    capabilities: List[str]
    min_plan: str
    entitled: bool
    enabled: bool
    disabled_by_org: bool


class RetrievalConfig(BaseModel):
    hybrid_enabled: bool = True
    reranker: str = "heuristic"
    rerank_top_n: int = 24


class ModelRouterView(BaseModel):
    plan_code: str
    default_model: str
    fallback_models: List[str]
    disabled_models: List[str]
    routing_strategy: str = "balanced"
    monthly_budget_usd: Optional[float] = None
    max_latency_ms: Optional[int] = None
    current_month_spend_usd: float = 0.0
    budget_exceeded: bool = False
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    models: List[ModelInfo]


class ModelPolicyUpdate(BaseModel):
    default_model: str = Field(..., min_length=1, max_length=80)
    fallback_models: List[str] = Field(default_factory=list)
    disabled_models: List[str] = Field(default_factory=list)
    routing_strategy: Optional[str] = None
    monthly_budget_usd: Optional[float] = Field(default=None, ge=0)
    max_latency_ms: Optional[int] = Field(default=None, ge=0)
    hybrid_enabled: Optional[bool] = None
    reranker: Optional[str] = None


class ResolveRequest(BaseModel):
    requested_model: str | None = None


class ResolveResponse(BaseModel):
    requested_model: str | None = None
    resolved_model: str

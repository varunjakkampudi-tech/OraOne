"""Pydantic schemas for the org analytics API (Phase 12, Module 6)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AnalyticsTotals(BaseModel):
    agents: int
    conversations: int
    messages: int
    workflows: int
    workflow_runs: int
    knowledge_bases: int
    documents: int
    members: int
    qualified_conversations: int
    conversion_rate: float


class SeriesPoint(BaseModel):
    date: str
    count: int


class AnalyticsSeries(BaseModel):
    conversations: list[SeriesPoint]
    messages: list[SeriesPoint]
    workflow_runs: list[SeriesPoint]


class AnalyticsBreakdowns(BaseModel):
    conversations_by_channel: dict[str, int]
    conversations_by_status: dict[str, int]
    workflow_runs_by_status: dict[str, int]


class TopAgent(BaseModel):
    agent_id: str
    name: str
    conversations: int


class OrgAnalyticsResponse(BaseModel):
    range_days: int
    generated_at: datetime
    totals: AnalyticsTotals
    series: AnalyticsSeries
    breakdowns: AnalyticsBreakdowns
    top_agents: list[TopAgent]

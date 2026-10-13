from __future__ import annotations

import uuid

import pytest
from sqlalchemy.dialects import postgresql


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _AnalyticsSession:
    def __init__(self, agent_id):
        from app.database.models.agent import AgentStatus

        self.agent_id = agent_id
        self.scalar_statements = []
        self.execute_statements = []
        self.agent_row = (
            agent_id,
            "Selected agent",
            AgentStatus.active,
            2,
            1,
        )

    async def scalar(self, statement):
        self.scalar_statements.append(statement)
        return 1

    async def execute(self, statement):
        self.execute_statements.append(statement)
        if len(self.execute_statements) == 1:
            return _Result([])
        return _Result([self.agent_row])


@pytest.mark.asyncio
async def test_agent_analytics_exact_agent_project_tenant_and_date_scope():
    from app.services.analytics_service import agent_analytics

    organization_id = uuid.uuid4()
    project_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    session = _AnalyticsSession(agent_id)

    result = await agent_analytics(
        session,
        organization_id,
        days=30,
        agent_id=agent_id,
        project_id=project_id,
    )

    assert result["totals"]["agents"] == 1
    assert [item["agent_id"] for item in result["agents"]] == [str(agent_id)]

    sql = str(
        session.execute_statements[1].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": False},
        )
    )
    assert "agents.id" in sql
    assert "agents.project_id" in sql
    assert "agents.organization_id" in sql
    assert "conversations.organization_id" in sql
    assert "conversations.project_id" in sql
    assert "conversations.created_at" in sql


@pytest.mark.asyncio
async def test_analytics_module_forwards_agent_filter_only_to_agents(monkeypatch):
    from app.api.analytics import routes
    from app.middleware.org_context import OrgContext
    from app.middleware.project_context import ProjectContext

    organization_id = uuid.uuid4()
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    ctx = OrgContext(
        user_id=user_id,
        cognito_sub="test-sub",
        organization_id=organization_id,
        membership_role="owner",
    )
    pctx = ProjectContext(
        user_id=user_id,
        organization_id=organization_id,
        membership_role="owner",
        project_id=project_id,
        project_slug="default",
        is_default_project=True,
    )
    calls = []

    async def fake_agents(session, org_id, days, **kwargs):
        calls.append(("agents", session, org_id, days, kwargs))
        return {}

    async def fake_knowledge(session, org_id, days):
        calls.append(("knowledge", session, org_id, days))
        return {}

    monkeypatch.setitem(routes.analytics_service.MODULE_FUNCTIONS, "agents", fake_agents)
    monkeypatch.setitem(
        routes.analytics_service.MODULE_FUNCTIONS, "knowledge", fake_knowledge
    )

    session = object()
    await routes.analytics_module(
        "agents",
        days=30,
        agent_id=agent_id,
        ctx=ctx,
        pctx=pctx,
        session=session,
    )
    await routes.analytics_module(
        "knowledge",
        days=30,
        agent_id=agent_id,
        ctx=ctx,
        pctx=pctx,
        session=session,
    )

    assert calls[0] == (
        "agents",
        session,
        organization_id,
        30,
        {"agent_id": agent_id, "project_id": project_id},
    )
    assert calls[1] == ("knowledge", session, organization_id, 30)

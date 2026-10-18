"""Contract tests for assistant-specific knowledge-base bindings."""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.agents.routes import _to_read_model, _validate_knowledge_base_ids
from app.database.models.agent import AgentStatus, AgentType
from app.services.agent_runtime import AgentRuntime
from app.schemas.agents import AgentCreate, AgentUpdate

TEST_PROJECT_ID = uuid.uuid4()


def test_knowledge_binding_omitted_is_distinct_from_explicit_empty():
    omitted_create = AgentCreate(name="A", type="chat")
    empty_create = AgentCreate(name="A", type="chat", knowledge_base_ids=[])
    omitted_update = AgentUpdate()
    empty_update = AgentUpdate(knowledge_base_ids=[])

    assert "knowledge_base_ids" not in omitted_create.model_fields_set
    assert omitted_create.model_dump(exclude_unset=True) == {
        "name": "A",
        "type": "chat",
    }
    assert empty_create.model_fields_set == {"name", "type", "knowledge_base_ids"}
    assert empty_create.knowledge_base_ids == []
    assert "knowledge_base_ids" not in omitted_update.model_fields_set
    assert empty_update.model_fields_set == {"knowledge_base_ids"}
    assert empty_update.knowledge_base_ids == []


def test_read_model_preserves_missing_and_explicit_empty_binding():
    now = datetime.now(timezone.utc)
    base = dict(
        id=uuid4(),
        organization_id=uuid4(),
        name="A",
        description=None,
        type=AgentType.chat,
        status=AgentStatus.draft,
        model="google/gemini-2.5-flash",
        avatar_url=None,
        created_at=now,
        updated_at=now,
        project_id=uuid4(),
    )

    config_defaults = dict(
        system_prompt=None,
        temperature=0.7,
        voice=None,
        language="en-US",
        greeting=None,
        max_tokens=1024,
    )
    missing = SimpleNamespace(
        **base,
        config=SimpleNamespace(config={}, **config_defaults),
    )
    explicit_empty = SimpleNamespace(
        **base,
        config=SimpleNamespace(
            config={"knowledge_base_ids": []},
            **config_defaults,
        ),
    )

    assert _to_read_model(missing).knowledge_base_ids is None
    assert _to_read_model(explicit_empty).knowledge_base_ids == []


class _ScalarResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class _Session:
    def __init__(self, values):
        self.values = values

    async def scalars(self, _statement):
        return _ScalarResult(self.values)


@pytest.mark.asyncio
async def test_binding_validation_requires_all_ids_in_active_org_project():
    organization_id = uuid4()
    project_id = uuid4()
    allowed = uuid4()
    other = uuid4()

    normalized = await _validate_knowledge_base_ids(
        _Session([allowed]),
        knowledge_base_ids=[allowed, allowed],
        organization_id=organization_id,
        project_id=project_id,
    )
    assert normalized == [allowed]

    with pytest.raises(HTTPException) as exc_info:
        await _validate_knowledge_base_ids(
            _Session([allowed]),
            knowledge_base_ids=[allowed, other],
            organization_id=organization_id,
            project_id=project_id,
        )
    assert exc_info.value.status_code == 422
    assert "active project" in str(exc_info.value.detail)


def test_runtime_distinguishes_omitted_and_explicit_empty_binding():
    runtime = object.__new__(AgentRuntime)
    omitted = SimpleNamespace(project_id=None, config=SimpleNamespace(config={}))
    explicit_empty = SimpleNamespace(
        project_id=None, config=SimpleNamespace(config={"knowledge_base_ids": []})
    )

    assert runtime._linked_kb_ids(SimpleNamespace(config=None)) is None
    assert runtime._linked_kb_ids(omitted) is None
    assert runtime._linked_kb_ids(explicit_empty) == []


@pytest.mark.asyncio
async def test_runtime_explicit_empty_binding_skips_rag(monkeypatch):
    runtime = object.__new__(AgentRuntime)
    runtime.session = object()
    runtime.ctx = SimpleNamespace(organization_id=uuid4())
    agent = SimpleNamespace(
        project_id=None, config=SimpleNamespace(config={"knowledge_base_ids": []})
    )

    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("RAG search must be skipped for an explicit empty binding")

    monkeypatch.setattr(
        "app.services.agent_runtime.rag_service.search_chunks", fail_if_called
    )
    assert await runtime.retrieve_context(agent, "should not search") == []


@pytest.mark.asyncio
async def test_runtime_omitted_binding_keeps_rag_fallback(monkeypatch):
    runtime = object.__new__(AgentRuntime)
    runtime.session = object()
    runtime.ctx = SimpleNamespace(organization_id=uuid4())
    agent = SimpleNamespace(project_id=None, config=SimpleNamespace(config={}))
    calls = []

    async def record_search(*_args, **kwargs):
        calls.append(kwargs["knowledge_base_ids"])
        return []

    monkeypatch.setattr(
        "app.services.agent_runtime.rag_service.search_chunks", record_search
    )
    assert await runtime.retrieve_context(agent, "uses fallback") == []
    assert calls == [None]


@pytest.fixture(autouse=True)
def _default_project_for_tests(monkeypatch):
    """Customer paths resolve a project. These tests have no project rows, so
    the organization default is pinned to one fixed project."""
    from app.services import project_scope

    project = uuid.uuid4()

    async def _default(_session, _organization_id):
        return project

    monkeypatch.setattr(project_scope, "default_project_id", _default)

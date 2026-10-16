"""Focused tests for None-versus-empty knowledge scope handling."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services import rag_service, workflow_engine


@pytest.mark.asyncio
async def test_hybrid_search_explicit_empty_allowlist_returns_without_querying(
    monkeypatch,
):
    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("empty allowlists must not query the database")

    monkeypatch.setattr(rag_service, "_base_query", fail_if_called)

    assert (
        await rag_service.hybrid_search(
            object(), "question", uuid4(), knowledge_base_ids=[]
        )
        == []
    )


@pytest.mark.asyncio
async def test_hybrid_search_none_preserves_legacy_all_kb_scope(monkeypatch):
    organization_id = uuid4()
    calls = []

    def record_base(org_id, kb_ids, project_id):
        calls.append((org_id, kb_ids, project_id))
        return object()

    async def no_candidates(*_args, **_kwargs):
        return []

    monkeypatch.setattr(rag_service, "_base_query", record_base)
    monkeypatch.setattr(rag_service, "_vector_candidates", no_candidates)
    monkeypatch.setattr(rag_service, "_fts_candidates", no_candidates)
    monkeypatch.setattr(rag_service, "_keyword_search", no_candidates)

    assert await rag_service.hybrid_search(object(), "question", organization_id) == []
    assert calls == [(organization_id, None, None)]


@pytest.mark.asyncio
async def test_workflow_kb_query_preserves_omitted_and_explicit_empty_scope(
    monkeypatch,
):
    calls = []

    async def record_search(*_args, **kwargs):
        calls.append(kwargs["knowledge_base_ids"])
        return []

    monkeypatch.setattr(workflow_engine.rag_service, "search_chunks", record_search)
    workflow = SimpleNamespace(organization_id=uuid4())

    await workflow_engine._step_kb_query(
        object(), workflow, {"query": "legacy fallback"}, {}
    )
    await workflow_engine._step_kb_query(
        object(), workflow, {"query": "explicit none", "knowledge_base_ids": []}, {}
    )

    assert calls == [None, []]

"""Every RAG inference must respect the configured model boundary."""

import uuid
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services import rag_answer

TEST_PROJECT_ID = uuid.uuid4()


@pytest.mark.asyncio
async def test_followups_respect_operator_model_pin(monkeypatch):
    calls = []

    class Provider:
        async def chat(self, messages, **kwargs):
            calls.append(kwargs["model"])
            return SimpleNamespace(
                content="First question?\nSecond question?\nThird question?"
            )

    monkeypatch.setenv("AI_FORCE_MODEL", "openrouter/free")
    monkeypatch.setattr(rag_answer, "get_provider", lambda: Provider())
    assert rag_answer._effective_model("paid/model") == "openrouter/free"
    await rag_answer._related_questions("question", [], True, model="paid/model")
    assert calls == ["openrouter/free"]


def test_unpinned_model_preserves_explicit_selection(monkeypatch):
    monkeypatch.delenv("AI_FORCE_MODEL", raising=False)
    assert rag_answer._effective_model("requested/model") == "requested/model"


@pytest.mark.asyncio
async def test_explicit_empty_scope_skips_hybrid_search(monkeypatch):
    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("hybrid_search must not run for an explicit empty scope")

    monkeypatch.setattr(rag_answer.rag_service, "hybrid_search", fail_if_called)

    result = await rag_answer.answer_query(
        object(),
        "question with no allowed knowledge bases",
        uuid4(),
        knowledge_base_ids=[],
        persona=None,
        project_id=TEST_PROJECT_ID,
    )

    assert result["sources"] == []
    assert result["context_chunks"] == 0
    assert result["grounded"] is False

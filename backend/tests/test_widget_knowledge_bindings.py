"""Isolated public-widget knowledge-scope contract tests."""

from types import SimpleNamespace
from uuid import uuid4

from app.api.widgets.public import _effective_knowledge_base_ids


def _agent(config):
    return SimpleNamespace(config=SimpleNamespace(config=config))


def _widget(knowledge_base_id=None):
    return SimpleNamespace(knowledge_base_id=knowledge_base_id)


def test_widget_preserves_legacy_fallback_when_agent_binding_is_omitted():
    kb_id = uuid4()

    assert _effective_knowledge_base_ids(_agent({}), _widget()) is None
    assert _effective_knowledge_base_ids(_agent({}), _widget(kb_id)) == [kb_id]


def test_widget_intersects_explicit_agent_binding_with_widget_binding():
    allowed = uuid4()
    other = uuid4()
    agent = _agent({"knowledge_base_ids": [str(allowed), str(other)]})

    assert _effective_knowledge_base_ids(agent, _widget()) == [allowed, other]
    assert _effective_knowledge_base_ids(agent, _widget(allowed)) == [allowed]
    assert _effective_knowledge_base_ids(agent, _widget(uuid4())) == []


def test_widget_explicit_empty_agent_binding_fails_closed():
    assert (
        _effective_knowledge_base_ids(_agent({"knowledge_base_ids": []}), _widget())
        == []
    )
    assert (
        _effective_knowledge_base_ids(
            _agent({"knowledge_base_ids": []}), _widget(uuid4())
        )
        == []
    )


def test_widget_malformed_explicit_agent_binding_fails_closed():
    assert (
        _effective_knowledge_base_ids(
            _agent({"knowledge_base_ids": ["not-a-uuid"]}), _widget()
        )
        == []
    )

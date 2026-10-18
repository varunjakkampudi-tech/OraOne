"""Assistants stay on the business.

No test contacts a real model or database. The provider is a counting fake and
knowledge retrieval is replaced with an in-memory store keyed by organization.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.database.models.agent import Agent, AgentStatus, AgentType
from app.database.models.agent_config import AgentConfig
from app.services import (
    assistant_profiles,
    business_scope_guard as guard,
    lead_service,
    omnichannel_service,
    rag_answer,
    rag_service,
    visitor_service,
    workflow_triggers,
)
from app.services.business_scope_guard import Scope

TEST_PROJECT_ID = uuid.uuid4()

# ───────────────────────────── fakes ─────────────────────────────


class CountingProvider:
    """Records every chat call. ``reply`` is returned verbatim as the content."""

    def __init__(self, reply: str = "", model: str = "test/model") -> None:
        self.reply = reply
        self.model = model
        self.calls: list[dict[str, Any]] = []

    async def chat(self, messages, **kwargs):
        self.calls.append({"messages": list(messages), **kwargs})
        return SimpleNamespace(content=self.reply, model=self.model, usage=None)


class FailingProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def chat(self, messages, **kwargs):
        self.calls += 1
        raise RuntimeError("model offline")


def _chunk(text: str, *, score: float = 0.9, name: str = "Business FAQ"):
    return rag_service.RetrievedChunk(
        content=text, chunk_index=0, document_name=name, score=score
    )


def _install_retrieval(monkeypatch, store: dict[uuid.UUID, list]) -> list[dict]:
    """Retrieval that only ever returns passages for the requested organization."""
    calls: list[dict] = []

    async def fake_search(session, query, organization_id, **kwargs):
        calls.append({"organization_id": organization_id, "query": query, **kwargs})
        return list(store.get(organization_id, []))

    async def fake_config(session, organization_id):
        return {}

    monkeypatch.setattr(rag_service, "hybrid_search", fake_search)
    monkeypatch.setattr(
        rag_answer.model_router_service, "retrieval_config", fake_config
    )
    return calls


def _install_provider(monkeypatch, provider) -> None:
    monkeypatch.setattr(rag_answer, "get_provider", lambda: provider)


def _system_text(call: dict) -> str:
    return "\n".join(m.content for m in call["messages"] if m.role == "system")


# ───────────────────────── deterministic scope rules ─────────────────────────

OUT_OF_SCOPE_QUESTIONS = [
    "Write me a poem about the moon",
    "Who is the president of France?",
    "Tell me a joke",
    "What is the capital of Australia?",
    "Write a Python function that reverses a string",
    "Should I break up with my boyfriend?",
    "Can you diagnose this rash for me?",
    "What's the weather going to be tomorrow?",
    "Which horoscope sign is best for March?",
]

IN_SCOPE_QUESTIONS = [
    "How much does shipping cost?",
    "Can I reschedule my appointment?",
    "What is your refund policy?",
    "Do you have this in size M?",
    "What are your opening hours on Saturday?",
    "Is the delivery free for orders over fifty?",
]


@pytest.mark.parametrize("text", OUT_OF_SCOPE_QUESTIONS)
def test_general_questions_are_classified_out_of_scope(text):
    assert guard.classify(text) is Scope.OUT_OF_SCOPE


@pytest.mark.parametrize("text", IN_SCOPE_QUESTIONS)
def test_business_questions_are_classified_in_scope(text):
    assert guard.classify(text) is Scope.IN_SCOPE


def test_business_words_do_not_override_a_strong_out_of_scope_request():
    assert guard.classify("Write a poem about our product prices") is Scope.OUT_OF_SCOPE


def test_promo_code_is_business_not_coding():
    assert guard.classify("Does this promo code work?") is Scope.IN_SCOPE


def test_greetings_are_small_talk_and_unknown_text_is_ambiguous():
    assert guard.classify("hello there") is Scope.SMALL_TALK
    assert guard.classify("thanks!") is Scope.SMALL_TALK
    assert guard.classify("the bronze package for two") is Scope.AMBIGUOUS


def test_model_label_must_be_exact():
    assert guard.parse_label("IN_SCOPE") is Scope.IN_SCOPE
    assert guard.parse_label(" out_of_scope. ") is Scope.OUT_OF_SCOPE
    assert guard.parse_label("Probably in scope") is None
    assert guard.parse_label("") is None
    assert guard.parse_label(None) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("text", OUT_OF_SCOPE_QUESTIONS)
async def test_out_of_scope_questions_are_refused_without_a_model_call(
    monkeypatch, text
):
    provider = CountingProvider(reply="should never be used")
    _install_provider(monkeypatch, provider)
    retrieval = _install_retrieval(monkeypatch, {})

    result = await rag_answer.answer_query(
        object(),
        text,
        uuid.uuid4(),
        persona="Be friendly.",
        business_contact="https://example.test",
        project_id=TEST_PROJECT_ID,
    )

    assert provider.calls == []
    assert retrieval == []
    assert result["scope"] == "out_of_scope"
    assert result["generated"] is False
    assert result["grounded"] is False
    assert result["answer"].startswith("Sorry, I can only help")
    assert "https://example.test" in result["answer"]


@pytest.mark.asyncio
async def test_small_talk_is_answered_without_retrieval_or_model(monkeypatch):
    provider = CountingProvider(reply="should never be used")
    _install_provider(monkeypatch, provider)
    retrieval = _install_retrieval(monkeypatch, {})

    result = await rag_answer.answer_query(
        object(), "hi", uuid.uuid4(), project_id=TEST_PROJECT_ID
    )

    assert provider.calls == []
    assert retrieval == []
    assert result["scope"] == "small_talk"
    assert "this business" in result["answer"]


@pytest.mark.asyncio
async def test_in_scope_question_with_passage_is_answered_from_context(monkeypatch):
    org = uuid.uuid4()
    provider = CountingProvider(reply="Refunds take five business days [1].")
    _install_provider(monkeypatch, provider)
    _install_retrieval(
        monkeypatch,
        {org: [_chunk("Refunds are processed within five business days.")]},
    )

    result = await rag_answer.answer_query(
        object(),
        "What is your refund policy?",
        org,
        persona=None,
        project_id=TEST_PROJECT_ID,
    )

    assert result["scope"] == "in_scope"
    assert result["generated"] is True
    assert result["grounded"] is True
    assert result["handoff"] is False
    assert result["answer"] == "Refunds take five business days [1]."
    user_turn = provider.calls[0]["messages"][-1].content  # calls[1] is follow-ups
    assert "Refunds are processed within five business days." in user_turn


@pytest.mark.asyncio
async def test_ambiguous_question_with_passage_is_classified_by_fixed_label(
    monkeypatch,
):
    org = uuid.uuid4()
    provider = CountingProvider(reply="OUT_OF_SCOPE")
    _install_provider(monkeypatch, provider)
    _install_retrieval(monkeypatch, {org: [_chunk("The bronze package is for two.")]})

    result = await rag_answer.answer_query(
        object(), "the bronze package for two", org, project_id=TEST_PROJECT_ID
    )

    assert len(provider.calls) == 1, "only the classifier may run"
    assert provider.calls[0]["max_tokens"] <= 5
    assert result["scope"] == "out_of_scope"
    assert result["answer"].startswith("Sorry, I can only help")


@pytest.mark.asyncio
async def test_ambiguous_question_with_unclear_label_proceeds_to_grounded_answer(
    monkeypatch,
):
    org = uuid.uuid4()
    provider = CountingProvider(reply="Maybe")
    _install_provider(monkeypatch, provider)
    _install_retrieval(monkeypatch, {org: [_chunk("The bronze package is for two.")]})

    # The fixed-label classifier call returns "Maybe". The answer call returns a
    # reply the passage supports, so the grounding check keeps it.
    chat = provider.chat

    async def _labelled(messages, **kwargs):
        if kwargs.get("max_tokens", 999) <= 5:
            return await chat(messages, **kwargs)
        provider.calls.append({"messages": list(messages), **kwargs})
        return SimpleNamespace(
            content="The bronze package is for two.", model=provider.model, usage=None
        )

    provider.chat = _labelled
    result = await rag_answer.answer_query(
        object(), "the bronze package", org, project_id=TEST_PROJECT_ID
    )

    assert result["scope"] == "in_scope"
    assert result["grounded"] is True
    assert result["generated"] is True


# ───────────────────────────── grounding and handoff ─────────────────────────────


@pytest.mark.asyncio
async def test_no_passage_hands_off_and_never_calls_the_model(monkeypatch):
    provider = CountingProvider(reply="general knowledge answer")
    _install_provider(monkeypatch, provider)
    _install_retrieval(monkeypatch, {})

    result = await rag_answer.answer_query(
        object(),
        "What is the price of the blue widget?",
        uuid.uuid4(),
        persona="You are a friendly shop assistant.",
        project_id=TEST_PROJECT_ID,
    )

    assert provider.calls == []
    assert result["handoff"] is True
    assert result["answer"] == rag_answer.HANDOFF_TEXT
    assert result["grounded"] is False
    assert result["generated"] is False
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_model_saying_it_lacks_information_becomes_a_handoff(monkeypatch):
    org = uuid.uuid4()
    provider = CountingProvider(
        reply="I don't have that information in the provided context."
    )
    _install_provider(monkeypatch, provider)
    _install_retrieval(monkeypatch, {org: [_chunk("We open at nine.")]})

    result = await rag_answer.answer_query(
        object(), "What is the price?", org, project_id=TEST_PROJECT_ID
    )

    assert result["handoff"] is True
    assert result["answer"] == rag_answer.HANDOFF_TEXT
    assert result["grounded"] is False
    assert result["generated"] is False


@pytest.mark.asyncio
async def test_extractive_fallback_is_grounded_but_not_generated(monkeypatch):
    org = uuid.uuid4()
    _install_provider(monkeypatch, FailingProvider())
    _install_retrieval(
        monkeypatch, {org: [_chunk("Refunds are processed within five business days.")]}
    )

    result = await rag_answer.answer_query(
        object(), "How long do refunds take?", org, project_id=TEST_PROJECT_ID
    )

    assert result["generated"] is False
    assert result["grounded"] is True
    assert "Refunds are processed" in result["answer"]


# ───────────────────────────── persona profiles ─────────────────────────────


@pytest.mark.parametrize("profile", assistant_profiles.PROFILES)
def test_every_persona_profile_contains_the_scope_and_grounding_rules(profile):
    prompt = assistant_profiles.system_prompt(profile)
    assert assistant_profiles.SCOPE_RULE in prompt
    assert assistant_profiles.GROUNDING_RULE in prompt


def test_profiles_add_their_own_style_on_top_of_the_base_rules():
    base = assistant_profiles.system_prompt("general")
    for profile in assistant_profiles.PROFILES:
        if profile == "general":
            continue
        style = assistant_profiles.PROFILE_STYLE[profile]
        assert style in assistant_profiles.system_prompt(profile)
        assert assistant_profiles.system_prompt(profile).startswith(base)


def test_unknown_profile_falls_back_to_general():
    assert assistant_profiles.system_prompt(
        "made_up"
    ) == assistant_profiles.system_prompt("general")


def test_resolve_profile_prefers_explicit_field_then_channel_then_general():
    assert (
        assistant_profiles.resolve_profile(
            {"assistant_profile": "marketing"}, "whatsapp"
        )
        == "marketing"
    )
    assert (
        assistant_profiles.resolve_profile({"assistant_profile": "bogus"}, "whatsapp")
        == "whatsapp_business"
    )
    assert assistant_profiles.resolve_profile(None, "instagram") == "instagram_dm"
    assert assistant_profiles.resolve_profile(None, "voice") == "call_centre"
    assert assistant_profiles.resolve_profile(None, "sms") == "general"
    assert assistant_profiles.resolve_profile({}, None) == "general"


def test_contact_hint_only_uses_the_owner_configured_url():
    assert assistant_profiles.contact_hint({"website_url": " https://shop.test "}) == (
        "https://shop.test"
    )
    assert assistant_profiles.contact_hint({}) is None
    assert assistant_profiles.contact_hint(None) is None


@pytest.mark.asyncio
async def test_profile_and_scope_rule_reach_the_model_prompt(monkeypatch):
    org = uuid.uuid4()
    provider = CountingProvider(reply="We open at nine [1].")
    _install_provider(monkeypatch, provider)
    _install_retrieval(monkeypatch, {org: [_chunk("We open at nine.")]})

    await rag_answer.answer_query(
        object(),
        "What time do you open?",
        org,
        persona="Use a cheerful tone.",
        assistant_profile="call_centre",
        project_id=TEST_PROJECT_ID,
    )

    system = _system_text(provider.calls[0])
    assert assistant_profiles.SCOPE_RULE in system
    assert assistant_profiles.PROFILE_STYLE["call_centre"] in system
    assert "Use a cheerful tone." in system


# ───────────────────────────── refusal wording ─────────────────────────────


def test_refusal_and_handoff_text_contain_no_invented_facts():
    refusal = rag_answer._refusal_text(None)
    for text in (refusal, rag_answer.HANDOFF_TEXT):
        assert not any(ch.isdigit() for ch in text)
        assert "http" not in text.lower()
        assert "@" not in text
    assert "contact the business." in refusal


def test_refusal_only_repeats_the_owner_contact_it_was_given():
    text = rag_answer._refusal_text("https://shop.test")
    assert "https://shop.test" in text
    assert text.count("http") == 1


# ───────────────────────────── tenant isolation ─────────────────────────────


@pytest.mark.asyncio
async def test_prompts_never_contain_another_tenants_knowledge(monkeypatch):
    org_a, org_b = uuid.uuid4(), uuid.uuid4()
    store = {
        org_a: [_chunk("Acme Bakery opens at seven.", name="Acme FAQ")],
        org_b: [
            _chunk("Rival Cafe secret discount is ninety percent.", name="Rival FAQ")
        ],
    }
    provider = CountingProvider(reply="We open at seven [1].")
    _install_provider(monkeypatch, provider)
    calls = _install_retrieval(monkeypatch, store)

    await rag_answer.answer_query(
        object(),
        "What time do you open?",
        org_a,
        persona="Be helpful.",
        extra_context="visitor remembers Acme",
        assistant_profile="website_owner",
        business_contact="https://acme.test",
        project_id=TEST_PROJECT_ID,
    )

    assert {c["organization_id"] for c in calls} == {org_a}
    all_prompts = "\n".join(m.content for c in provider.calls for m in c["messages"])
    assert "Acme Bakery" in all_prompts
    assert "Rival" not in all_prompts
    assert "secret discount" not in all_prompts
    assert str(org_a) not in all_prompts
    assert str(org_b) not in all_prompts


@pytest.mark.asyncio
async def test_other_tenants_passages_do_not_answer_a_question(monkeypatch):
    org_a, org_b = uuid.uuid4(), uuid.uuid4()
    store = {org_b: [_chunk("Rival Cafe is open on Sundays.")]}
    provider = CountingProvider(reply="should never be used")
    _install_provider(monkeypatch, provider)
    _install_retrieval(monkeypatch, store)

    result = await rag_answer.answer_query(
        object(), "Are you open on Sundays?", org_a, project_id=TEST_PROJECT_ID
    )

    assert result["handoff"] is True
    assert provider.calls == []


# ───────────────────────────── omnichannel wiring ─────────────────────────────


class _RecordingSession:
    """Accepts adds and flushes; the agent lookup returns the supplied row."""

    def __init__(self, agent_row: Any = None) -> None:
        self._agent_row = agent_row
        self.added: list[Any] = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def scalar(self, _stmt):
        return self._agent_row


def _inbound(channel: str = "whatsapp") -> omnichannel_service.InboundMessage:
    return omnichannel_service.InboundMessage(
        channel=channel,
        organization_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        text="What is the price of the blue widget?",
        phone="+14155550123",
    )


def _patch_omnichannel(monkeypatch, answer_result: dict, recorded: dict) -> None:
    async def _claim(_session, _msg):
        return True

    async def _thread(_session, _msg, _profile, _channel):
        return SimpleNamespace(id=uuid.uuid4(), last_message_at=None)

    async def _upsert_profile(*_args, **_kwargs):
        return SimpleNamespace(id=uuid.uuid4())

    async def _answer(session, text, org_id, **kwargs):
        recorded["answer_kwargs"] = kwargs
        return answer_result

    async def _lead(session, **kwargs):
        recorded.setdefault("leads", []).append(kwargs)
        return SimpleNamespace()

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(omnichannel_service, "_claim_provider_message", _claim)
    monkeypatch.setattr(omnichannel_service, "_find_or_create_thread", _thread)
    monkeypatch.setattr(omnichannel_service, "answer_query", _answer)
    monkeypatch.setattr(lead_service, "upsert_conversation_lead", _lead)
    monkeypatch.setattr(visitor_service, "upsert_profile", _upsert_profile)
    monkeypatch.setattr(visitor_service, "link_conversation", lambda *a, **k: None)
    monkeypatch.setattr(visitor_service, "build_memory_digest", lambda *a, **k: "")
    monkeypatch.setattr(visitor_service, "append_memory", lambda *a, **k: None)
    monkeypatch.setattr(workflow_triggers, "fire_message_received", _noop)


@pytest.mark.asyncio
async def test_omnichannel_handoff_creates_a_lead_note_and_uses_channel_profile(
    monkeypatch,
):
    recorded: dict = {}
    _patch_omnichannel(
        monkeypatch,
        {
            "answer": rag_answer.HANDOFF_TEXT,
            "grounded": False,
            "generated": False,
            "handoff": True,
            "confidence": 0.0,
            "model": None,
        },
        recorded,
    )
    session = _RecordingSession(agent_row=None)

    reply = await omnichannel_service.handle_inbound(session, _inbound("whatsapp"))

    assert reply.text == rag_answer.HANDOFF_TEXT
    assert recorded["answer_kwargs"]["assistant_profile"] == "whatsapp_business"
    assert len(recorded["leads"]) == 1
    assert recorded["leads"][0]["source"] == "whatsapp"


@pytest.mark.asyncio
async def test_omnichannel_passes_owner_persona_and_contact(monkeypatch):
    recorded: dict = {}
    _patch_omnichannel(
        monkeypatch,
        {"answer": "Ok", "grounded": True, "generated": True, "confidence": 0.9},
        recorded,
    )
    agent = Agent(
        status=AgentStatus.active, name="Shop", type=AgentType.whatsapp, model="m"
    )
    agent.config = AgentConfig(
        system_prompt="Keep it brief.",
        config={
            "assistant_profile": "small_business",
            "website_url": "https://shop.test",
        },
    )
    session = _RecordingSession(agent_row=agent)

    await omnichannel_service.handle_inbound(session, _inbound("whatsapp"))

    kwargs = recorded["answer_kwargs"]
    assert kwargs["persona"] == "Keep it brief."
    assert kwargs["assistant_profile"] == "small_business"
    assert kwargs["business_contact"] == "https://shop.test"
    assert recorded.get("leads") is None


@pytest.fixture(autouse=True)
def _default_project_for_tests(monkeypatch):
    """Customer paths resolve a project. These tests have no project rows, so
    the organization default is pinned to one fixed project."""
    from app.services import project_scope

    project = uuid.uuid4()

    async def _default(_session, _organization_id):
        return project

    monkeypatch.setattr(project_scope, "default_project_id", _default)

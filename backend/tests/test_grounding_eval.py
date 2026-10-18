"""Answer-level grounding: the verifier's verdicts on a versioned evaluation set,
and the answer path's behaviour when a model reply goes beyond its passages.

No network and no real model: the provider is replaced with a canned reply.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import grounding, rag_answer, rag_service

DATASET = Path(__file__).parent / "fixtures" / "grounding_eval.json"
REQUIRED_CATEGORIES = {"supported", "unsupported_claim", "injection", "multilingual"}


def _load_cases() -> dict:
    return json.loads(DATASET.read_text(encoding="utf-8"))


def test_evaluation_set_is_versioned_and_covers_the_risk_categories():
    data = _load_cases()
    assert data["version"] == 1
    categories = {case["category"] for case in data["cases"]}
    assert REQUIRED_CATEGORIES <= categories


def test_verifier_matches_every_expected_verdict():
    data = _load_cases()
    mismatches = []
    for case in data["cases"]:
        flagged = grounding.unsupported_sentences(case["answer"], case["passages"])
        verdict = "unsupported" if flagged else "supported"
        if verdict != case["expected"]:
            mismatches.append((case["id"], verdict, case["expected"], flagged))
    assert mismatches == [], f"verifier disagreed with the evaluation set: {mismatches}"


class _CannedProvider:
    def __init__(self, content: str):
        self._content = content

    async def chat(self, *_args, **_kwargs):
        return SimpleNamespace(content=self._content, model="test-model", usage=None)


def _one_passage(text: str):
    async def _search(*_args, **_kwargs):
        return [
            rag_service.RetrievedChunk(
                content=text,
                chunk_index=0,
                document_name="Policy",
                score=0.9,
            )
        ]

    return _search


@pytest.mark.asyncio
async def test_invented_reply_falls_back_to_the_passage_text(monkeypatch):
    passage = "Refunds are processed within five business days."
    monkeypatch.setattr(rag_answer.rag_service, "hybrid_search", _one_passage(passage))
    monkeypatch.setattr(
        rag_answer,
        "get_provider",
        lambda: _CannedProvider(
            "Refunds are instant and never take longer than one hour."
        ),
    )

    result = await rag_answer.answer_query(
        object(),
        "How long do refunds take?",
        uuid.uuid4(),
        persona=None,
        project_id=uuid.uuid4(),
    )

    assert "five business days" in result["answer"]
    assert "one hour" not in result["answer"]
    assert result["generated"] is False


@pytest.mark.asyncio
async def test_supported_reply_is_kept_as_generated(monkeypatch):
    passage = "Refunds are processed within five business days."
    monkeypatch.setattr(rag_answer.rag_service, "hybrid_search", _one_passage(passage))
    monkeypatch.setattr(
        rag_answer,
        "get_provider",
        lambda: _CannedProvider("Refunds take five business days."),
    )

    result = await rag_answer.answer_query(
        object(),
        "How long do refunds take?",
        uuid.uuid4(),
        persona=None,
        project_id=uuid.uuid4(),
    )

    assert result["answer"] == "Refunds take five business days."
    assert result["generated"] is True

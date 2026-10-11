"""Bonus AI assistants (lightweight, prompt-driven).

A small family of operator-facing AI helpers that all reuse the *same* provider
stack (:func:`app.providers.get_provider`) — there is no separate AI engine.
Each assistant is a system prompt + a builder that turns a free-form input dict
into a user message, and a STRICT-JSON contract. Every call degrades gracefully
to a deterministic stub so the UI never hard-fails when the model is offline.

Assistants
----------
* ``meeting``        — summarise a call/meeting transcript into actions.
* ``qa``             — score a conversation for quality + coaching.
* ``forecast``       — project next-period metrics from recent numbers.
* ``personalize``    — craft a personalised outreach message.
* ``experiment``     — pick an A/B winner and suggest improvements.
* ``copilot``        — general how-do-I copilot for operators.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Optional

from app.providers import ChatMessage, DEFAULT_MODEL, get_provider

log = logging.getLogger("app.assistants")


def _extract_json(text: str) -> Optional[dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        brace, last = text.find("{"), text.rfind("}")
        if brace != -1 and last != -1 and last > brace:
            text = text[brace : last + 1]
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _str(payload: dict[str, Any], key: str, default: str = "") -> str:
    return str(payload.get(key) or default).strip()


# ─────────────────────────── per-assistant builders ──────────────────────────

def _meeting_user(p: dict[str, Any]) -> str:
    return (
        "Summarise this conversation transcript.\n"
        f"Context: {_str(p, 'context', 'N/A')}\n\n"
        f"Transcript:\n{_str(p, 'transcript')}\n\n"
        "Return JSON: {summary, action_items[], decisions[], follow_ups[], sentiment}."
    )


def _qa_user(p: dict[str, Any]) -> str:
    return (
        "You are a contact-centre QA reviewer. Score this conversation for quality.\n"
        f"Goal of the call: {_str(p, 'goal', 'help the customer')}\n\n"
        f"Transcript:\n{_str(p, 'transcript')}\n\n"
        "Return JSON: {score (0-100 integer), summary, strengths[], issues[], coaching[]}."
    )


def _forecast_user(p: dict[str, Any]) -> str:
    return (
        "You are a revenue/operations analyst. Project the next period from these numbers.\n"
        f"Metric: {_str(p, 'metric', 'interactions')}\n"
        f"Recent values (oldest→newest): {_str(p, 'history', 'N/A')}\n"
        f"Horizon: {_str(p, 'horizon', 'next 7 periods')}\n\n"
        "Return JSON: {forecast[] (numbers), trend (up|down|flat), drivers[], risks[], summary}."
    )


def _personalize_user(p: dict[str, Any]) -> str:
    return (
        "Write a short, personalised outreach message for this customer.\n"
        f"Customer: {_str(p, 'customer', 'a customer')}\n"
        f"Context / history: {_str(p, 'context', 'N/A')}\n"
        f"Channel: {_str(p, 'channel', 'email')}\n"
        f"Goal: {_str(p, 'goal', 'win them back')}\n"
        f"Tone: {_str(p, 'tone', 'warm and professional')}\n\n"
        "Return JSON: {message, subject, tone, next_best_action, talking_points[]}."
    )


def _experiment_user(p: dict[str, Any]) -> str:
    return (
        "You are a growth/CRO expert. Compare these two variants for the stated goal.\n"
        f"Goal / metric: {_str(p, 'goal', 'click-through rate')}\n"
        f"Variant A: {_str(p, 'variant_a')}\n"
        f"Variant B: {_str(p, 'variant_b')}\n\n"
        "Return JSON: {recommended_variant (A|B), confidence (low|medium|high), rationale, suggestions[]}."
    )


def _copilot_user(p: dict[str, Any]) -> str:
    return (
        "You are OraOne Copilot, a helpful in-app assistant for an AI customer-experience "
        "platform (agents, knowledge bases, chat/WhatsApp channels, campaigns, analytics).\n"
        f"Operator question: {_str(p, 'question')}\n\n"
        "Return JSON: {answer, steps[], related[]}."
    )


# ─────────────────────────── fallback shapes ─────────────────────────────────

def _meeting_fb(p):
    return {"summary": "AI summary unavailable — review the transcript manually.",
            "action_items": [], "decisions": [], "follow_ups": [], "sentiment": "neutral"}


def _qa_fb(p):
    return {"score": 0, "summary": "AI review unavailable.", "strengths": [], "issues": [], "coaching": []}


def _forecast_fb(p):
    return {"forecast": [], "trend": "flat", "drivers": [], "risks": [],
            "summary": "AI forecast unavailable — not enough signal."}


def _personalize_fb(p):
    cust = _str(p, "customer", "there")
    return {"message": f"Hi {cust}, just checking in — we'd love to help you get more from OraOne.",
            "subject": "Quick check-in", "tone": _str(p, "tone", "warm"),
            "next_best_action": "Follow up in 3 days", "talking_points": []}


def _experiment_fb(p):
    return {"recommended_variant": "A", "confidence": "low",
            "rationale": "AI comparison unavailable — defaulting to control.", "suggestions": []}


def _copilot_fb(p):
    return {"answer": "I couldn't reach the AI service just now. Please try again shortly.",
            "steps": [], "related": []}


# ─────────────────────────── registry ────────────────────────────────────────

class _Assistant:
    def __init__(self, *, key, label, description, icon, system,
                 build: Callable[[dict], str], fallback: Callable[[dict], dict],
                 temperature: float = 0.5, max_tokens: int = 900):
        self.key = key
        self.label = label
        self.description = description
        self.icon = icon
        self.system = system
        self.build = build
        self.fallback = fallback
        self.temperature = temperature
        self.max_tokens = max_tokens


_STRICT = "Respond with ONLY a single valid JSON object, no prose, no code fences."

ASSISTANTS: dict[str, _Assistant] = {
    a.key: a for a in [
        _Assistant(
            key="meeting", label="Meeting Assistant", icon="📝",
            description="Turn call & meeting transcripts into summaries and action items.",
            system="You summarise business conversations into crisp, actionable notes. " + _STRICT,
            build=_meeting_user, fallback=_meeting_fb,
        ),
        _Assistant(
            key="qa", label="Quality Assurance", icon="✅",
            description="Score conversations and generate agent coaching tips.",
            system="You are a rigorous but fair contact-centre QA reviewer. " + _STRICT,
            build=_qa_user, fallback=_qa_fb, temperature=0.3,
        ),
        _Assistant(
            key="forecast", label="Forecasting", icon="📈",
            description="Project next-period metrics from recent history.",
            system="You are a pragmatic analyst who forecasts conservatively. " + _STRICT,
            build=_forecast_user, fallback=_forecast_fb, temperature=0.2,
        ),
        _Assistant(
            key="personalize", label="Personalization", icon="🎯",
            description="Craft personalised outreach for a specific customer.",
            system="You write concise, human, personalised customer messages. " + _STRICT,
            build=_personalize_user, fallback=_personalize_fb, temperature=0.7,
        ),
        _Assistant(
            key="experiment", label="A/B Testing", icon="🧪",
            description="Compare two variants and recommend a winner.",
            system="You are a conversion-rate-optimisation expert. " + _STRICT,
            build=_experiment_user, fallback=_experiment_fb, temperature=0.4,
        ),
        _Assistant(
            key="copilot", label="Copilot", icon="💡",
            description="Ask how to do anything in OraOne.",
            system="You are OraOne Copilot, friendly and concise. " + _STRICT,
            build=_copilot_user, fallback=_copilot_fb, temperature=0.4,
        ),
    ]
}


def catalog() -> list[dict[str, str]]:
    return [
        {"key": a.key, "label": a.label, "description": a.description, "icon": a.icon}
        for a in ASSISTANTS.values()
    ]


async def run(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Run an assistant; always returns {result, generated}."""
    assistant = ASSISTANTS.get(kind)
    if assistant is None:
        raise KeyError(kind)
    try:
        provider = get_provider()
        resp = await provider.chat(
            [
                ChatMessage(role="system", content=assistant.system),
                ChatMessage(role="user", content=assistant.build(payload)),
            ],
            model=DEFAULT_MODEL,
            temperature=assistant.temperature,
            max_tokens=assistant.max_tokens,
        )
        data = _extract_json(resp.content)
        if data:
            return {"result": data, "generated": True}
    except Exception as e:  # noqa: BLE001 — degrade gracefully
        log.info("assistant %s fell back: %s", kind, e)
    return {"result": assistant.fallback(payload), "generated": False}

"""Agent lifecycle helpers.

Agents behave like cloud services, not apps the user starts by hand:

    draft → (deploy / channel connected) → active ⇄ paused → archived

The single hard requirement before an agent may serve traffic is a
non-empty system prompt. ``readiness`` exposes that as a per-row signal so
the UI can warn about incomplete agents and the API can refuse to activate
them.
"""
from __future__ import annotations

from app.database.models.agent import Agent, AgentStatus


def missing_requirements(agent: Agent) -> list[str]:
    """Human-readable list of what's still needed before an agent can go live."""
    missing: list[str] = []
    cfg = getattr(agent, "config", None)
    prompt = (cfg.system_prompt if cfg else None) or ""
    if not prompt.strip():
        missing.append("a system prompt")
    return missing


def is_ready(agent: Agent) -> bool:
    """True when the agent meets the minimum requirements to serve traffic."""
    return not missing_requirements(agent)


def can_serve(agent: Agent) -> bool:
    """True only when the agent is published and actively answering."""
    return agent.status == AgentStatus.active

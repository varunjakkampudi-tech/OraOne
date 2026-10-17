"""Workflow engine (Phase 11).

Executes a workflow's steps sequentially, threading a mutable ``context``
dict of variables between them. Each step reads its config (with
``{{var}}`` interpolation against the context), does its work, and writes
an output variable back into the context for downstream steps.

Runs in its own ``AsyncSession`` so it's safe to launch from FastAPI
``BackgroundTasks``. Every row it writes is stamped with the workflow's
``organization_id``.

Step types
----------
* ``ai_prompt``     — call the LLM with a templated prompt
* ``ai_classify``   — classify text into one of N categories (JSON)
* ``ai_extract``    — extract structured fields into JSON
* ``ai_summarize``  — summarise text
* ``ai_sentiment``  — positive / negative / neutral
* ``ai_translate``  — translate to a target language
* ``kb_query``      — RAG retrieval from the org's knowledge bases
* ``agent_run``     — run one of the org's configured agents
* ``transform``     — render a template into a new variable
* ``condition``     — stop the run unless a predicate holds
* ``approval``      — pause for a human decision (resumes via the API)
* ``notification``  — record a notification (log sink for now)
* ``delay``         — durable wait: persisted and resumed by the scheduler, never slept
* ``send_message``  — outbound message on the lead's channel (stored as notification);
  consent is checked first, then the message goes through the org's enabled
  channel binding (see ``workflow_senders``). Unconfigured channels fail with a reason.
* ``create_task``   — task record linked to the lead (stored as transform)
* ``webhook``       — outbound HTTP POST (http/https only)

Each step also supports ``retry`` (extra attempts) and
``continue_on_error`` (don't fail the whole run) in its config.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import re
import socket
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Protocol
from urllib.parse import urlsplit

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.models.agent import Agent
from app.database.models.collaboration import Task, TaskStatus
from app.database.models.conversation import Conversation
from app.database.models.lead import Lead
from app.database.models.message import Message, MessageSender
from app.database.models.workflow import (
    RunStatus,
    RunStepStatus,
    StepType,
    Workflow,
    WorkflowRun,
    WorkflowRunStep,
    WorkflowStatus,
    WorkflowTrigger,
)
from app.database.session import AsyncSessionLocal, init_engine
from app.middleware.org_context import OrgContext
from app.providers import DEFAULT_MODEL, get_provider
from app.providers.base import AIProviderError, ChatMessage
from app.services import rag_service
from app.services.agent_runtime import AgentRuntime
from app.services.audit import audit
from app.services import contact_policy_service
from app.services.outreach_policy import ContactState, check_outbound
from app.services.workflow_senders import (
    SUPPORTED_CHANNELS,
    ChannelOutboundSender,
    OutboundNotConfigured,
)

log = logging.getLogger("app.workflow")

_MAX_OUTPUT_CHARS = 20_000
_MAX_RETRIES = 5
_MAX_RETRY_DELAY = 30
_TEMPLATE_RE = re.compile(r"{{\s*([a-zA-Z0-9_.]+)\s*}}")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _maker():
    if AsyncSessionLocal is None:
        init_engine()
    from app.database.session import AsyncSessionLocal as Maker

    return Maker


# ───────────────────────── public entry points ─────────────────────────


async def execute_run(run_id: uuid.UUID) -> None:
    """Background entry point for a fresh run. Owns its own DB session."""
    ensure_default_senders()
    Maker = _maker()
    async with Maker() as session:  # type: ignore[misc]
        try:
            await _start(session, run_id)
        except Exception as exc:  # pragma: no cover - last-resort guard
            log.exception("workflow run %s crashed: %s", run_id, exc)
            await session.rollback()
            await _mark_run_failed(session, run_id, str(exc))


async def resume_run(run_id: uuid.UUID, *, approved: bool, note: str = "") -> None:
    """Resume a run that paused on a human-approval step."""
    ensure_default_senders()
    Maker = _maker()
    async with Maker() as session:  # type: ignore[misc]
        try:
            await _resume(session, run_id, approved=approved, note=note)
        except Exception as exc:  # pragma: no cover - last-resort guard
            log.exception("workflow resume %s crashed: %s", run_id, exc)
            await session.rollback()
            await _mark_run_failed(session, run_id, str(exc))


# ───────────────────────── orchestration ─────────────────────────


async def _load(session: AsyncSession, run_id: uuid.UUID):
    run = await session.get(WorkflowRun, run_id)
    if run is None:
        return None, None, []
    workflow = await session.get(Workflow, run.workflow_id)
    steps = list(
        (
            await session.scalars(
                select(WorkflowRunStep)
                .where(WorkflowRunStep.run_id == run.id)
                .order_by(WorkflowRunStep.order_index)
            )
        ).all()
    )
    return run, workflow, steps


async def _start(session: AsyncSession, run_id: uuid.UUID) -> None:
    if not await _claim_queued_run(session, run_id):
        log.info("workflow run %s is not queued; skipping", run_id)
        return
    run, workflow, steps = await _load(session, run_id)
    if run is None:
        log.warning("workflow run %s not found", run_id)
        return
    if workflow is None:
        await _mark_run_failed(session, run_id, "Workflow no longer exists.")
        return
    if (
        run.trigger == WorkflowTrigger.event
        and workflow.status != WorkflowStatus.active
    ):
        run.status = RunStatus.cancelled
        run.error_message = "The workflow was paused before this event ran."
        run.finished_at = _utcnow()
        await session.commit()
        return

    context: dict[str, Any] = dict(run.input or {})
    context.setdefault(
        "trigger",
        run.trigger.value if hasattr(run.trigger, "value") else str(run.trigger),
    )
    await _run_loop(session, workflow, run, steps, context, start_index=0)


async def _resume(
    session: AsyncSession, run_id: uuid.UUID, *, approved: bool, note: str
) -> None:
    run, workflow, steps = await _load(session, run_id)
    if run is None or workflow is None:
        return
    if run.status != RunStatus.awaiting_approval:
        log.info("resume ignored: run %s is %s", run_id, run.status)
        return
    # Claim the pause before any step runs. Two decisions can both read the run as
    # waiting; only the one whose conditional UPDATE matches continues, so approval
    # steps and the sends after them run once.
    if not await _claim_awaiting_approval(session, run_id):
        log.info("resume ignored: run %s was already decided", run_id)
        return

    # Restore the paused context.
    context: dict[str, Any] = dict(run.output or {})

    idx = next(
        (i for i, s in enumerate(steps) if s.status == RunStepStatus.awaiting_approval),
        None,
    )
    if idx is None:
        await _finalize(session, workflow, run, context, failed=False, error=None)
        return

    astep = steps[idx]
    if not approved:
        astep.status = RunStepStatus.skipped
        astep.output = {
            "decision": "rejected",
            "note": note,
            "text": "Rejected by reviewer.",
        }
        astep.finished_at = _utcnow()
        run.status = RunStatus.cancelled
        run.error_message = (
            "Rejected at approval step." + (f" {note}" if note else "")
        )[:2000]
        run.finished_at = _utcnow()
        workflow.run_count += 1
        workflow.last_run_at = run.finished_at
        await session.commit()
        _audit_run(workflow, run)
        return

    astep.status = RunStepStatus.completed
    astep.output = {
        "decision": "approved",
        "note": note,
        "text": "Approved by reviewer.",
    }
    astep.finished_at = _utcnow()
    run.steps_completed += 1
    run.status = RunStatus.running
    await session.commit()
    await _run_loop(session, workflow, run, steps, context, start_index=idx + 1)


async def _run_loop(
    session: AsyncSession,
    workflow: Workflow,
    run: WorkflowRun,
    steps: list[WorkflowRunStep],
    context: dict[str, Any],
    *,
    start_index: int,
) -> None:
    lead: Optional[Lead] = None
    lead_loaded = False

    for position in range(start_index, len(steps)):
        rstep = steps[position]
        stype = _type_value(rstep.type)
        cfg = dict(rstep.config or {})

        # Human-approval step: pause the run and persist context for resume.
        if stype == StepType.approval.value:
            rstep.status = RunStepStatus.awaiting_approval
            rstep.started_at = _utcnow()
            rstep.input = _safe_json(context)
            rstep.output = {
                "prompt": _render(
                    str(cfg.get("message", "Approval required.")), context
                ),
                "text": _render(str(cfg.get("message", "Approval required.")), context),
            }
            run.status = RunStatus.awaiting_approval
            run.output = _safe_json(context)  # checkpoint for resume
            await session.commit()
            _audit_run(workflow, run, extra={"paused": True})
            return

        if _needs_lead(stype, cfg) and not lead_loaded:
            lead = await _load_lead(session, workflow, context)
            lead_loaded = True

        rstep.status = RunStepStatus.running
        rstep.started_at = _utcnow()
        rstep.input = _safe_json(context)
        await session.commit()

        if stype == StepType.delay.value:
            try:
                seconds = _wait_seconds(cfg)
            except ValueError as exc:
                outcome = _Outcome("failed", reason=str(exc))
            else:
                if seconds > 0:
                    await _pause_for_wait(session, run, rstep, context, seconds)
                    return  # resumed later by resume_due_waits()
                outcome = _Outcome(
                    "completed",
                    output={
                        "waited_seconds": 0,
                        "reason": "No wait was set, so the run continued at once.",
                    },
                )
        else:
            outcome = await _attempt_step(session, workflow, rstep, cfg, context, lead)

        if outcome.status == "skipped":
            rstep.status = RunStepStatus.skipped
            rstep.output = _safe_json({**outcome.output, "reason": outcome.reason})
            rstep.error_message = None
            rstep.finished_at = _utcnow()
            await session.commit()
            continue

        if outcome.status == "failed":
            rstep.status = RunStepStatus.failed
            rstep.error_message = outcome.reason[:2000]
            rstep.output = _safe_json({**outcome.output, "reason": outcome.reason})
            rstep.finished_at = _utcnow()
            if cfg.get("continue_on_error"):
                await session.commit()
                continue
            await _skip_remaining(
                session, steps, position + 1, "Not run because an earlier step failed."
            )
            await _finalize(
                session,
                workflow,
                run,
                context,
                failed=True,
                error=outcome.reason[:2000],
            )
            return

        rstep.output = _safe_json(outcome.output)
        rstep.status = RunStepStatus.completed
        rstep.finished_at = _utcnow()
        run.steps_completed += 1

        # A condition that is not met ends the run; the rest is logged as skipped.
        if outcome.output.get("_stop"):
            await _skip_remaining(
                session,
                steps,
                position + 1,
                "Not run because an earlier condition was not met.",
            )
            await session.commit()
            break
        await session.commit()

    await _finalize(session, workflow, run, context, failed=False, error=None)


async def _finalize(
    session: AsyncSession,
    workflow: Workflow,
    run: WorkflowRun,
    context: dict[str, Any],
    *,
    failed: bool,
    error: Optional[str],
) -> None:
    run.status = RunStatus.failed if failed else RunStatus.completed
    run.error_message = error
    run.output = _safe_json(context)
    run.finished_at = _utcnow()

    workflow.run_count += 1
    workflow.last_run_at = run.finished_at
    if not failed:
        workflow.success_count += 1
    await session.commit()
    _audit_run(workflow, run)


def _audit_run(
    workflow: Workflow, run: WorkflowRun, *, extra: Optional[dict] = None
) -> None:
    meta = {
        "run_id": str(run.id),
        "status": run.status.value,
        "steps": run.steps_completed,
    }
    if extra:
        meta.update(extra)
    audit(
        "run",
        resource="workflow",
        organization_id=str(workflow.organization_id),
        user_id=str(run.triggered_by) if run.triggered_by else "system",
        resource_id=str(workflow.id),
        meta=meta,
    )


async def _mark_run_failed(
    session: AsyncSession, run_id: uuid.UUID, message: str
) -> None:
    run = await session.get(WorkflowRun, run_id)
    if run is None:
        return
    run.status = RunStatus.failed
    run.error_message = message[:2000]
    run.finished_at = _utcnow()
    await session.commit()


# ───────────────────────── step dispatch ─────────────────────────


async def _run_step(
    session: AsyncSession,
    workflow: Workflow,
    rstep: WorkflowRunStep,
    context: dict[str, Any],
    lead: Optional[Lead] = None,
) -> dict[str, Any]:
    cfg = dict(rstep.config or {})
    stype = _type_value(rstep.type)
    action = cfg.get("action")

    if stype == StepType.notification.value and action == "send_message":
        return await _step_send_message(session, workflow, cfg, context, lead)
    if stype == StepType.transform.value and action == "create_task":
        return await _step_create_task(session, workflow, cfg, context, lead)

    if stype == StepType.ai_prompt.value:
        return await _step_ai_prompt(workflow, cfg, context)
    if stype == StepType.ai_classify.value:
        return await _step_ai_classify(workflow, cfg, context)
    if stype == StepType.ai_extract.value:
        return await _step_ai_extract(workflow, cfg, context)
    if stype == StepType.ai_summarize.value:
        return await _step_ai_summarize(workflow, cfg, context)
    if stype == StepType.ai_sentiment.value:
        return await _step_ai_sentiment(workflow, cfg, context)
    if stype == StepType.ai_translate.value:
        return await _step_ai_translate(workflow, cfg, context)
    if stype == StepType.kb_query.value:
        return await _step_kb_query(session, workflow, cfg, context)
    if stype == StepType.agent_run.value:
        return await _step_agent_run(session, workflow, cfg, context)
    if stype == StepType.transform.value:
        return _step_transform(cfg, context)
    if stype == StepType.condition.value:
        return _step_condition(cfg, context, lead)
    if stype == StepType.notification.value:
        return _step_notification(workflow, cfg, context)
    if stype == StepType.webhook.value:
        return await _step_webhook(cfg, context)

    raise ValueError(f"Unknown step type: {stype}")


# ───────────────────────── AI helpers ─────────────────────────


async def _chat(
    cfg: dict[str, Any],
    system: str,
    user: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    messages: list[ChatMessage] = []
    if system:
        messages.append(ChatMessage(role="system", content=system))
    messages.append(ChatMessage(role="user", content=user))
    provider = get_provider()
    try:
        resp = await provider.chat(
            messages,
            model=str(cfg.get("model") or DEFAULT_MODEL),
            temperature=float(cfg.get("temperature", temperature)),
            max_tokens=int(cfg.get("max_tokens", max_tokens)),
        )
    except AIProviderError as exc:
        raise RuntimeError(f"AI provider error ({exc.code}): {exc}") from exc
    return (resp.content or "")[:_MAX_OUTPUT_CHARS]


def _parse_json(text: str) -> Any:
    """Best-effort JSON extraction from an LLM response."""
    s = (text or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s).strip()
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"(\{.*\}|\[.*\])", s, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                return None
    return None


# ───────────────────────── step executors ─────────────────────────


async def _step_ai_prompt(
    workflow: Workflow, cfg: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    prompt = _render(str(cfg.get("prompt", "")), context).strip()
    if not prompt:
        raise ValueError("ai_prompt step requires a 'prompt'.")
    system = _render(str(cfg.get("system", "")), context).strip()
    text = await _chat(cfg, system, prompt, temperature=0.7)
    out_var = str(cfg.get("output_var") or "ai_output")
    context[out_var] = text
    return {"text": text, "output_var": out_var}


async def _step_ai_classify(
    workflow: Workflow, cfg: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    text_in = _render(str(cfg.get("input", cfg.get("text", ""))), context).strip()
    if not text_in:
        raise ValueError("ai_classify step requires 'input' text.")
    categories = cfg.get("categories") or []
    if isinstance(categories, str):
        categories = [c.strip() for c in categories.split(",") if c.strip()]
    if not categories:
        raise ValueError("ai_classify step requires 'categories'.")
    cats = ", ".join(str(c) for c in categories)
    system = (
        "You are a precise text classifier. Choose exactly one category from the "
        "allowed list. Respond ONLY with JSON: "
        '{"category": <one of the list>, "confidence": <0-1>, "reason": <short>}.'
    )
    user = f"Allowed categories: {cats}\n\nText:\n{text_in}"
    raw = await _chat(cfg, system, user)
    parsed = _parse_json(raw) or {}
    category = str(parsed.get("category") or "").strip()
    if category not in [str(c) for c in categories]:
        # Fall back to the closest literal match found in the response.
        category = next(
            (str(c) for c in categories if str(c).lower() in raw.lower()),
            str(categories[0]),
        )
    out_var = str(cfg.get("output_var") or "classification")
    context[out_var] = category
    return {
        "text": category,
        "category": category,
        "confidence": parsed.get("confidence"),
        "reason": parsed.get("reason"),
        "output_var": out_var,
    }


async def _step_ai_extract(
    workflow: Workflow, cfg: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    text_in = _render(str(cfg.get("input", cfg.get("text", ""))), context).strip()
    if not text_in:
        raise ValueError("ai_extract step requires 'input' text.")
    fields = cfg.get("fields") or []
    if isinstance(fields, str):
        fields = [f.strip() for f in fields.split(",") if f.strip()]
    if not fields:
        raise ValueError("ai_extract step requires 'fields'.")
    keys = ", ".join(str(f) for f in fields)
    system = (
        "Extract the requested fields from the text. Respond ONLY with a JSON "
        "object whose keys are exactly the requested field names. Use null when a "
        "field is not present."
    )
    user = f"Fields: {keys}\n\nText:\n{text_in}"
    raw = await _chat(cfg, system, user)
    data = _parse_json(raw)
    if not isinstance(data, dict):
        data = {}
    out_var = str(cfg.get("output_var") or "extracted")
    context[out_var] = data
    # Also surface individual fields for easy templating.
    for f in fields:
        context[str(f)] = data.get(str(f))
    return {
        "text": json.dumps(data, ensure_ascii=False),
        "data": data,
        "output_var": out_var,
    }


async def _step_ai_summarize(
    workflow: Workflow, cfg: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    text_in = _render(str(cfg.get("input", cfg.get("text", ""))), context).strip()
    if not text_in:
        raise ValueError("ai_summarize step requires 'input' text.")
    max_words = int(cfg.get("max_words", 120) or 120)
    system = (
        f"Summarise the text in at most {max_words} words. Be faithful and concise."
    )
    text = await _chat(cfg, system, text_in)
    out_var = str(cfg.get("output_var") or "summary")
    context[out_var] = text
    return {"text": text, "output_var": out_var}


async def _step_ai_sentiment(
    workflow: Workflow, cfg: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    text_in = _render(str(cfg.get("input", cfg.get("text", ""))), context).strip()
    if not text_in:
        raise ValueError("ai_sentiment step requires 'input' text.")
    system = (
        "Classify the sentiment of the text. Respond ONLY with JSON: "
        '{"sentiment": "positive"|"negative"|"neutral", "score": <-1..1>}.'
    )
    raw = await _chat(cfg, system, text_in)
    parsed = _parse_json(raw) or {}
    sentiment = str(parsed.get("sentiment") or "").lower().strip()
    if sentiment not in ("positive", "negative", "neutral"):
        low = raw.lower()
        sentiment = (
            "positive"
            if "positive" in low
            else "negative"
            if "negative" in low
            else "neutral"
        )
    out_var = str(cfg.get("output_var") or "sentiment")
    context[out_var] = sentiment
    return {
        "text": sentiment,
        "sentiment": sentiment,
        "score": parsed.get("score"),
        "output_var": out_var,
    }


async def _step_ai_translate(
    workflow: Workflow, cfg: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    text_in = _render(str(cfg.get("input", cfg.get("text", ""))), context).strip()
    if not text_in:
        raise ValueError("ai_translate step requires 'input' text.")
    target = (
        _render(str(cfg.get("target_language", "English")), context).strip()
        or "English"
    )
    system = f"Translate the user's text into {target}. Output only the translation."
    text = await _chat(cfg, system, text_in)
    out_var = str(cfg.get("output_var") or "translation")
    context[out_var] = text
    return {"text": text, "target_language": target, "output_var": out_var}


async def _step_kb_query(
    session: AsyncSession,
    workflow: Workflow,
    cfg: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    query = _render(str(cfg.get("query", "")), context).strip()
    if not query:
        raise ValueError("kb_query step requires a 'query'.")
    kb_ids_raw = cfg.get("knowledge_base_ids")
    kb_ids: Optional[list[uuid.UUID]] = (
        None if kb_ids_raw is None else [uuid.UUID(str(k)) for k in kb_ids_raw]
    )
    top_k = int(cfg.get("top_k", 5))

    chunks = await rag_service.search_chunks(
        session,
        query,
        workflow.organization_id,
        knowledge_base_ids=kb_ids,
        top_k=top_k,
    )
    joined = "\n\n".join(c.content for c in chunks)[:_MAX_OUTPUT_CHARS]
    out_var = str(cfg.get("output_var") or "kb_results")
    context[out_var] = joined
    return {
        "output_var": out_var,
        "match_count": len(chunks),
        "context": joined,
        "sources": [{"document": c.document_name, "score": c.score} for c in chunks],
    }


async def _step_agent_run(
    session: AsyncSession,
    workflow: Workflow,
    cfg: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    agent_id_raw = cfg.get("agent_id")
    if not agent_id_raw:
        raise ValueError("agent_run step requires an 'agent_id'.")
    agent_id = uuid.UUID(str(agent_id_raw))
    agent = await session.get(Agent, agent_id)
    if (
        agent is None
        or agent.organization_id != workflow.organization_id
        or agent.deleted_at is not None
    ):
        raise ValueError("Agent not found in this organization.")

    message = _render(str(cfg.get("message", "")), context).strip()
    if not message:
        raise ValueError("agent_run step requires a 'message'.")

    ctx = OrgContext(
        user_id=workflow.created_by or uuid.uuid4(),
        auth_subject="workflow",
        organization_id=workflow.organization_id,
        membership_role="system",
    )
    runtime = AgentRuntime(session, ctx)
    resp = await runtime.generate_reply(
        agent, [ChatMessage(role="user", content=message)]
    )
    text = (resp.content or "")[:_MAX_OUTPUT_CHARS]
    out_var = str(cfg.get("output_var") or "agent_output")
    context[out_var] = text
    return {"text": text, "output_var": out_var, "agent": agent.name}


def _step_transform(cfg: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    template = str(cfg.get("template", ""))
    rendered = _render(template, context)[:_MAX_OUTPUT_CHARS]
    out_var = str(cfg.get("output_var") or "transform_output")
    context[out_var] = rendered
    return {"output_var": out_var, "value": rendered}


def _step_condition(
    cfg: dict[str, Any], context: dict[str, Any], lead: Optional[Lead] = None
) -> dict[str, Any]:
    view = _render_context(context, lead)
    left = _render(str(cfg.get("left", "")), view)
    right = _render(str(cfg.get("right", "")), view)
    op = str(cfg.get("op", "contains")).lower()

    if op in ("eq", "=="):
        ok = left == right
    elif op in ("ne", "!="):
        ok = left != right
    elif op == "contains":
        ok = right.lower() in left.lower()
    elif op == "not_contains":
        ok = right.lower() not in left.lower()
    elif op in ("gt", ">"):
        ok = _as_float(left) > _as_float(right)
    elif op in ("lt", "<"):
        ok = _as_float(left) < _as_float(right)
    elif op in ("nonempty", "truthy"):
        ok = bool(left.strip())
    else:
        raise ValueError(f"Unknown condition op: {op}")

    # When the predicate fails we stop the run (successfully) unless the
    # author asked to keep going.
    stop = (not ok) and bool(cfg.get("stop_on_false", True))
    outcome = "met" if ok else "not met"
    return {
        "passed": ok,
        "reason": f"Condition {outcome}: compared '{left}' with '{right}' using {op}.",
        "_stop": stop,
        "op": op,
        "left": left,
        "right": right,
    }


def _step_notification(
    workflow: Workflow, cfg: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    channel = str(cfg.get("channel", "log"))
    message = _render(str(cfg.get("message", "")), context)[:_MAX_OUTPUT_CHARS]
    log.info(
        "WORKFLOW NOTIFY org=%s channel=%s :: %s",
        workflow.organization_id,
        channel,
        message,
    )
    # Log-only sink: nothing reaches a person, so the output says so.
    return {
        "channel": channel,
        "message": message,
        "text": message,
        "delivered": False,
        "reason": "Written to the server log only. No notification channel is configured.",
    }


_WEBHOOK_TIMEOUT_SECONDS = 15.0
_WEBHOOK_LOCAL_HOST = "localhost"


def _is_development() -> bool:
    return settings.environment == "development" and not settings.is_production


def _is_blocked_address(raw: str) -> bool:
    """True for any address a webhook must never reach: internal, reserved or non-public."""
    ip = ipaddress.ip_address(raw.split("%", 1)[0])  # drop an IPv6 zone id if present
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return bool(
        ip.is_loopback
        or ip.is_link_local  # includes 169.254.0.0/16 (cloud metadata)
        or ip.is_private  # RFC 1918 and fc00::/7
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
        or not ip.is_global
    )


async def _assert_public_webhook_target(url: str) -> None:
    """Refuse webhook URLs that are not https or that resolve to a non-public address.

    Every address returned by the resolver is checked, for IPv4 and IPv6. The one
    exception is plain http to ``localhost`` in a development environment.
    """
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if not host:
        raise ValueError("webhook url has no host.")
    if host == _WEBHOOK_LOCAL_HOST and _is_development():
        return
    if parts.scheme != "https":
        raise ValueError("webhook url must use https.")

    port = parts.port or 443
    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo, host, port, 0, socket.SOCK_STREAM
        )
    except OSError as exc:
        raise ValueError("webhook host could not be resolved.") from exc
    addresses = {info[4][0] for info in infos}
    if not addresses:
        raise ValueError("webhook host could not be resolved.")
    if any(_is_blocked_address(addr) for addr in addresses):
        raise ValueError(
            "webhook url resolves to a private or internal address and was not called."
        )


async def _step_webhook(cfg: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    url = _render(str(cfg.get("url", "")), context).strip()
    if not url or not url.lower().startswith(("http://", "https://")):
        raise ValueError("webhook step requires an http(s) 'url'.")
    import httpx

    from app.services.egress_guard import (
        UnsafeDestinationError,
        pinned_request,
        resolve_public_target,
    )

    # Resolve once, validate every address and connect to that validated IP so
    # the request cannot be rebound to a private address after the check.
    allow_plain_local = (
        urlsplit(url).hostname or ""
    ).lower() == _WEBHOOK_LOCAL_HOST and _is_development()
    if not allow_plain_local and urlsplit(url).scheme != "https":
        raise ValueError("webhook url must use https.")
    try:
        target = await asyncio.to_thread(
            resolve_public_target, url, allow_plain_local=allow_plain_local
        )
    except UnsafeDestinationError as exc:
        if exc.reason == "unresolvable":
            raise ValueError("webhook host could not be resolved.") from exc
        raise ValueError(
            "webhook url resolves to a private or internal address and was not called."
        ) from exc
    payload = cfg.get("payload")
    if isinstance(payload, str):
        payload = {"text": _render(payload, context)}
    elif isinstance(payload, dict):
        payload = {
            k: _render(str(v), context) if isinstance(v, str) else v
            for k, v in payload.items()
        }
    else:
        payload = {"context": _safe_json(context)}

    try:
        async with httpx.AsyncClient(
            timeout=_WEBHOOK_TIMEOUT_SECONDS, follow_redirects=False
        ) as client:
            resp = await pinned_request(client, "POST", target, json=payload)
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        # The connection was never made, so nothing was sent and a retry is safe.
        raise StepFailed(
            "The webhook could not be reached.", {"dispatched": False}
        ) from exc
    except httpx.HTTPError as exc:
        # The request may have reached the receiver, so it must not be sent again.
        raise StepFailed(
            "The webhook request failed after it was sent.", {"dispatched": True}
        ) from exc
    return {
        "status_code": resp.status_code,
        "ok": resp.is_success,
        "text": f"HTTP {resp.status_code}",
    }


# Durable waits may span days, but a single wait is bounded.
_MAX_WAIT_SECONDS = 30 * 86400
_PRIVATE_CHANNEL_FIELDS = {"whatsapp": "phone", "sms": "phone", "email": "email"}
# Instagram DMs are addressed by the lead's Instagram-scoped id, kept in lead.extra.
_INSTAGRAM_ID_KEY = "instagram_id"
_CONSENT_STATES = {
    "granted": "given",
    "given": "given",
    "denied": "withdrawn",
    "withdrawn": "withdrawn",
}
# Steps whose authored type has no stored enum value. They are saved as an
# existing StepType plus ``config.action`` (see normalise_step_type).
ACTION_STEP_TYPES: dict[str, tuple[StepType, Optional[str]]] = {
    "wait": (StepType.delay, None),
    "send_message": (StepType.notification, "send_message"),
    "create_task": (StepType.transform, "create_task"),
}


def _needs_lead(stype: str, cfg: dict[str, Any]) -> bool:
    """Condition, send_message and create_task read the lead; the rest do not."""
    if stype == StepType.condition.value:
        return True
    return cfg.get("action") in ("send_message", "create_task")


class StepSkipped(Exception):
    """A step decided not to act, for example because consent does not allow a send."""

    def __init__(self, reason: str, output: Optional[dict[str, Any]] = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.output = output or {}


class StepFailed(Exception):
    """A step could not do its work. The message is shown to the user as the reason."""

    def __init__(self, reason: str, output: Optional[dict[str, Any]] = None) -> None:
        super().__init__(reason)
        self.output = output or {}


@dataclass
class _Outcome:
    status: str  # completed | skipped | failed
    reason: str = ""
    output: dict[str, Any] = field(default_factory=dict)


class OutboundSender(Protocol):
    """Delivers one outbound message on one channel. Raises on failure."""

    async def send(
        self,
        *,
        channel: str,
        recipient: str,
        text: str,
        organization_id: uuid.UUID,
        lead_id: uuid.UUID,
    ) -> None: ...


_OUTBOUND_SENDERS: dict[str, OutboundSender] = {}


def register_outbound_sender(channel: str, sender: OutboundSender) -> None:
    """Connect a channel to the send_message step. No sender means no send."""
    _OUTBOUND_SENDERS[channel] = sender


def unregister_outbound_sender(channel: str) -> None:
    _OUTBOUND_SENDERS.pop(channel, None)


def get_outbound_sender(channel: str) -> Optional[OutboundSender]:
    return _OUTBOUND_SENDERS.get(channel)


def ensure_default_senders() -> None:
    """Connect each supported channel to the real channel-adapter sender.

    Called by the production entry points. An explicitly registered sender for a
    channel is kept as it is, so tests and callers can still substitute one.
    """
    sender = ChannelOutboundSender()
    for channel in SUPPORTED_CHANNELS:
        _OUTBOUND_SENDERS.setdefault(channel, sender)


def normalise_step_type(
    declared: str, config: dict[str, Any]
) -> tuple[StepType, dict[str, Any]]:
    """Map an authored step type to the stored StepType and config.

    Raises ValueError for an unknown type.
    """
    if declared in ACTION_STEP_TYPES:
        stored, action = ACTION_STEP_TYPES[declared]
        cfg = dict(config or {})
        if action:
            cfg["action"] = action
        return stored, cfg
    try:
        return StepType(declared), dict(config or {})
    except ValueError:
        raise ValueError(f"Unknown step type '{declared}'.") from None


def _type_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def lead_lookup_stmt(
    organization_id: uuid.UUID, lead_id: Any, conversation_id: Any
) -> Optional[Any]:
    """Select the lead a run is about, scoped to the workflow's organization."""
    stmt = select(Lead).where(
        Lead.organization_id == organization_id, Lead.deleted_at.is_(None)
    )
    try:
        if lead_id:
            return stmt.where(Lead.id == uuid.UUID(str(lead_id))).limit(1)
        if conversation_id:
            return (
                stmt.where(Lead.conversation_id == uuid.UUID(str(conversation_id)))
                .order_by(Lead.created_at.desc())
                .limit(1)
            )
    except ValueError:
        return None
    return None


def _lead_view(lead: Lead) -> dict[str, Any]:
    def plain(value: Any) -> Any:
        return value.value if hasattr(value, "value") else value

    return {
        "name": lead.name or "",
        "email": lead.email or "",
        "phone": lead.phone or "",
        "company": lead.company or "",
        "intent": lead.intent or "",
        "source": lead.source or "",
        "status": plain(lead.status) or "",
        "temperature": plain(lead.temperature) or "",
        "score": lead.score if lead.score is not None else "",
    }


def _render_context(context: dict[str, Any], lead: Optional[Lead]) -> dict[str, Any]:
    view = dict(context)
    if lead is not None:
        view["lead"] = _lead_view(lead)
    return view


def _wait_seconds(cfg: dict[str, Any]) -> int:
    try:
        total = (
            int(cfg.get("seconds") or 0)
            + 60 * int(cfg.get("minutes") or 0)
            + 3600 * int(cfg.get("hours") or 0)
            + 86400 * int(cfg.get("days") or 0)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "A wait step needs whole numbers for seconds, minutes, hours or days."
        ) from exc
    if total < 0:
        raise ValueError("A wait step cannot be negative.")
    if total > _MAX_WAIT_SECONDS:
        raise ValueError("A wait step can be at most 30 days.")
    return total


def _describe_seconds(seconds: int) -> str:
    for size, unit in ((86400, "day"), (3600, "hour"), (60, "minute")):
        if seconds >= size and seconds % size == 0:
            count = seconds // size
            return f"{count} {unit}{'' if count == 1 else 's'}"
    return f"{seconds} second{'' if seconds == 1 else 's'}"


async def _pause_for_wait(
    session: AsyncSession,
    run: WorkflowRun,
    rstep: WorkflowRunStep,
    context: dict[str, Any],
    seconds: int,
) -> None:
    """Persist a durable wait. The scheduler resumes it; nothing sleeps here."""
    resume_at = _utcnow() + timedelta(seconds=seconds)
    rstep.status = RunStepStatus.running
    rstep.output = {
        "waiting": True,
        "seconds": seconds,
        "resume_at": resume_at.isoformat(),
        "reason": (
            f"Waiting {_describe_seconds(seconds)}. The run resumes at "
            f"{resume_at:%Y-%m-%d %H:%M} UTC."
        ),
    }
    run.status = RunStatus.running
    run.output = _safe_json(context)  # checkpoint for the resume
    await session.commit()


def _wait_is_due(step: WorkflowRunStep, now: datetime) -> bool:
    out = step.output or {}
    if not out.get("waiting"):
        return False
    try:
        resume_at = datetime.fromisoformat(str(out.get("resume_at")))
    except ValueError:
        return False
    if resume_at.tzinfo is None:
        resume_at = resume_at.replace(tzinfo=timezone.utc)
    return resume_at <= now


async def _claim_queued_run(session: AsyncSession, run_id: uuid.UUID) -> bool:
    """Move a queued run to running in one atomic update, so it executes once."""
    result = await session.execute(
        update(WorkflowRun)
        .where(WorkflowRun.id == run_id, WorkflowRun.status == RunStatus.queued)
        .values(status=RunStatus.running, started_at=_utcnow())
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    return (result.rowcount or 0) == 1


async def _claim_awaiting_approval(session: AsyncSession, run_id: uuid.UUID) -> bool:
    """Move a run waiting on approval to running in one atomic update. Only one caller wins.

    The row lock from this UPDATE is held until the caller's next commit. A concurrent
    claim waits for that commit, then re-checks its WHERE clause and matches nothing.
    """
    result = await session.execute(
        update(WorkflowRun)
        .where(
            WorkflowRun.id == run_id,
            WorkflowRun.status == RunStatus.awaiting_approval,
        )
        .values(status=RunStatus.running)
        .execution_options(synchronize_session=False)
    )
    return (result.rowcount or 0) == 1


async def _skip_remaining(
    session: AsyncSession, steps: list[WorkflowRunStep], from_index: int, reason: str
) -> None:
    """Give every step that will not run a skipped row with the reason."""
    now = _utcnow()
    for rest in steps[from_index:]:
        if rest.status in (None, RunStepStatus.pending):
            rest.status = RunStepStatus.skipped
            rest.output = {"reason": reason}
            rest.finished_at = now
    await session.commit()


async def _load_lead(
    session: AsyncSession, workflow: Workflow, context: dict[str, Any]
) -> Optional[Lead]:
    stmt = lead_lookup_stmt(
        workflow.organization_id, context.get("lead_id"), context.get("conversation_id")
    )
    if stmt is None:
        return None
    return await session.scalar(stmt)


def _policy_consent(raw: Any) -> str:
    return _CONSENT_STATES.get(str(raw or "").lower(), "unknown")


async def _last_inbound_at(session: AsyncSession, lead: Lead) -> Optional[datetime]:
    if lead.conversation_id is None:
        return None
    value = await session.scalar(
        select(func.max(Message.created_at))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Conversation.id == lead.conversation_id,
            Conversation.organization_id == lead.organization_id,
            Message.sender == MessageSender.customer,
        )
    )
    if value is not None and value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


async def _attempts_last_24h(
    session: AsyncSession, organization_id: uuid.UUID, lead_id: uuid.UUID
) -> int:
    since = _utcnow() - timedelta(hours=24)
    count = await session.scalar(
        select(func.count(WorkflowRunStep.id)).where(
            WorkflowRunStep.organization_id == organization_id,
            WorkflowRunStep.type == StepType.notification,
            WorkflowRunStep.output["lead_id"].astext == str(lead_id),
            WorkflowRunStep.output["dispatched"].astext == "true",
            WorkflowRunStep.finished_at >= since,
        )
    )
    return int(count or 0)


async def _outbound_channel(
    session: AsyncSession, cfg: dict[str, Any], lead: Lead
) -> str:
    explicit = str(cfg.get("channel") or "").strip().lower()
    if explicit:
        return explicit
    if lead.conversation_id is not None:
        value = await session.scalar(
            select(Conversation.channel).where(
                Conversation.id == lead.conversation_id,
                Conversation.organization_id == lead.organization_id,
            )
        )
        if value is not None:
            return _type_value(value)
    return str(lead.source or "").lower()


def _recipient_for(channel: str, lead: Lead) -> str:
    if channel == "instagram":
        value = (lead.extra or {}).get(_INSTAGRAM_ID_KEY)
        if not value:
            raise StepFailed(
                "The lead has no Instagram account id for instagram messages."
            )
        return str(value)
    field_name = _PRIVATE_CHANNEL_FIELDS.get(channel)
    if field_name is None:
        raise StepFailed(
            f"Messages cannot be sent on the {channel} channel. "
            "Set the step channel to whatsapp, sms, instagram or email."
        )
    value = getattr(lead, field_name)
    if not value:
        noun = "email address" if field_name == "email" else "phone number"
        raise StepFailed(f"The lead has no {noun} for {channel}.")
    return str(value)


async def _consent_decision(
    session: AsyncSession, cfg: dict[str, Any], lead: Lead, channel: str
):
    extra = lead.extra or {}
    tz_name = extra.get("timezone")
    on_do_not_contact = await contact_policy_service.is_lead_suppressed(
        session, lead=lead, channel=channel
    )
    state = ContactState(
        consent=_policy_consent(extra.get("consent")),
        suppressed=on_do_not_contact or bool(extra.get("suppressed")),
        opted_out=bool(extra.get("opted_out")),
        timezone=tz_name if isinstance(tz_name, str) and tz_name else None,
        last_inbound_at=await _last_inbound_at(session, lead),
        attempts_last_24h=await _attempts_last_24h(
            session, lead.organization_id, lead.id
        ),
    )
    return check_outbound(
        contact=state,
        channel=channel,  # type: ignore[arg-type]
        now=_utcnow(),
        org_timezone=str(cfg.get("org_timezone") or "UTC"),
    )


async def _step_send_message(
    session: AsyncSession,
    workflow: Workflow,
    cfg: dict[str, Any],
    context: dict[str, Any],
    lead: Optional[Lead],
) -> dict[str, Any]:
    if lead is None:
        raise StepFailed("This step needs a lead, and this run has no lead attached.")
    channel = await _outbound_channel(session, cfg, lead)
    recipient = _recipient_for(channel, lead)
    text = _render(str(cfg.get("message", "")), _render_context(context, lead)).strip()
    if not text:
        raise StepFailed("The send_message step has no message text.")

    base: dict[str, Any] = {
        "lead_id": str(lead.id),
        "channel": channel,
        "dispatched": False,
    }
    decision = await _consent_decision(session, cfg, lead, channel)
    if not decision.allowed:
        raise StepSkipped("Not sent. " + " ".join(decision.reasons), base)

    sender = get_outbound_sender(channel)
    if sender is None:
        raise StepFailed(
            f"No outbound adapter is configured for {channel}, so the message was not sent.",
            base,
        )
    base["dispatched"] = True
    try:
        details = await sender.send(
            channel=channel,
            recipient=recipient,
            text=text,
            organization_id=workflow.organization_id,
            lead_id=lead.id,
        )
    except OutboundNotConfigured as exc:
        # Nothing left the server, so this attempt does not count toward the daily cap.
        raise StepFailed(str(exc), {**base, "dispatched": False}) from exc
    except Exception as exc:  # noqa: BLE001 - provider detail is not shown to users
        log.warning(
            "outbound %s send failed for lead %s: %s",
            channel,
            lead.id,
            type(exc).__name__,
        )
        raise StepFailed(
            f"The {channel} provider did not accept the message.", base
        ) from exc
    # Senders may return which provider and binding carried the message.
    extra = details if isinstance(details, dict) else {}
    return {
        **base,
        **extra,
        "sent": True,
        "text": text[:500],
        "reason": f"Sent a {channel} message to the lead.",
    }


async def _step_create_task(
    session: AsyncSession,
    workflow: Workflow,
    cfg: dict[str, Any],
    context: dict[str, Any],
    lead: Optional[Lead],
) -> dict[str, Any]:
    view = _render_context(context, lead)
    title = _render(str(cfg.get("title", "")), view).strip()
    if not title:
        raise StepFailed("The create_task step needs a title.")
    description = _render(str(cfg.get("description", "")), view).strip() or None
    due_at = None
    if cfg.get("due_in_hours") not in (None, ""):
        try:
            hours = int(cfg["due_in_hours"])
        except (TypeError, ValueError) as exc:
            raise StepFailed("due_in_hours must be a whole number.") from exc
        if not 0 <= hours <= 24 * 365:
            raise StepFailed("due_in_hours must be between 0 and 8760.")
        due_at = _utcnow() + timedelta(hours=hours)
    task = Task(
        organization_id=workflow.organization_id,
        title=title[:255],
        description=description,
        status=TaskStatus.OPEN,
        created_by_user_id=workflow.created_by,
        resource_type="lead" if lead is not None else None,
        resource_id=str(lead.id) if lead is not None else None,
        due_at=due_at,
    )
    session.add(task)
    await session.flush()
    return {
        "task_id": str(task.id),
        "title": task.title,
        "reason": f"Created task '{task.title}'.",
    }


async def _attempt_step(
    session: AsyncSession,
    workflow: Workflow,
    rstep: WorkflowRunStep,
    cfg: dict[str, Any],
    context: dict[str, Any],
    lead: Optional[Lead],
) -> _Outcome:
    attempts = 1 + min(max(int(cfg.get("retry", 0) or 0), 0), _MAX_RETRIES)
    retry_delay = min(max(int(cfg.get("retry_delay", 2) or 0), 0), _MAX_RETRY_DELAY)
    last_exc: Optional[Exception] = None
    made = 0
    for attempt in range(attempts):
        made = attempt + 1
        try:
            output = await _run_step(session, workflow, rstep, context, lead)
            return _Outcome("completed", output={**(output or {}), "attempts": made})
        except StepSkipped as skip:
            return _Outcome(
                "skipped", reason=skip.reason, output={**skip.output, "attempts": made}
            )
        except Exception as exc:  # noqa: BLE001 - recorded per step
            last_exc = exc
            log.warning(
                "step %s attempt %d/%d failed: %s",
                rstep.name,
                attempt + 1,
                attempts,
                exc,
            )
            if _may_have_been_dispatched(exc):
                # The message may already be with the provider. Retrying could send it twice.
                log.warning(
                    "step %s not retried: the send may have been delivered", rstep.name
                )
                break
            if attempt < attempts - 1 and retry_delay:
                await asyncio.sleep(retry_delay)
    reason = str(last_exc)[:2000] if last_exc is not None else "Step failed."
    return _Outcome(
        "failed",
        reason=reason,
        output={
            **dict(getattr(last_exc, "output", None) or {}),
            "attempts": made,
        },
    )


def _may_have_been_dispatched(exc: Exception) -> bool:
    """True when a step's outbound send may already have left the server."""
    return bool((getattr(exc, "output", None) or {}).get("dispatched"))


# ───────────────────────── durable waits ─────────────────────────


async def resume_due_waits(now: Optional[datetime] = None) -> int:
    """Resume durable waits whose time has come. Called by the scheduler tick."""
    now = now or _utcnow()
    ensure_default_senders()
    Maker = _maker()
    async with Maker() as session:  # type: ignore[misc]
        candidates = list(
            (
                await session.scalars(
                    select(WorkflowRunStep)
                    .join(WorkflowRun, WorkflowRun.id == WorkflowRunStep.run_id)
                    .where(
                        WorkflowRunStep.status == RunStepStatus.running,
                        WorkflowRunStep.type == StepType.delay,
                        WorkflowRun.status == RunStatus.running,
                    )
                    .limit(200)
                )
            ).all()
        )
    due = [(s.run_id, s.id) for s in candidates if _wait_is_due(s, now)]
    resumed = 0
    for run_id, step_id in due:
        try:
            if await _resume_wait(run_id, step_id, now):
                resumed += 1
        except Exception as exc:  # noqa: BLE001 - one bad run must not stop the rest
            log.exception("resuming wait step %s failed: %s", step_id, exc)
    return resumed


async def _resume_wait(run_id: uuid.UUID, step_id: uuid.UUID, now: datetime) -> bool:
    Maker = _maker()
    async with Maker() as session:  # type: ignore[misc]
        claim = await session.execute(
            update(WorkflowRunStep)
            .where(
                WorkflowRunStep.id == step_id,
                WorkflowRunStep.status == RunStepStatus.running,
            )
            .values(status=RunStepStatus.completed, finished_at=now)
            .execution_options(synchronize_session=False)
        )
        if (claim.rowcount or 0) != 1:
            await session.rollback()
            return False
        run, workflow, steps = await _load(session, run_id)
        idx = next((i for i, s in enumerate(steps) if s.id == step_id), None)
        if (
            run is None
            or workflow is None
            or idx is None
            or run.status != RunStatus.running
        ):
            await session.commit()
            return False
        steps[idx].output = _safe_json(
            {"waited": True, "reason": "Wait finished. The run continued."}
        )
        run.steps_completed += 1
        context: dict[str, Any] = dict(run.output or {})
        await session.commit()
        await _run_loop(session, workflow, run, steps, context, start_index=idx + 1)
        return True


# ───────────────────────── helpers ─────────────────────────


def _render(template: str, context: dict[str, Any]) -> str:
    """Substitute ``{{var}}`` tokens from ``context`` (supports dotted keys)."""

    def repl(m: "re.Match[str]") -> str:
        key = m.group(1)
        val: Any = context
        for part in key.split("."):
            if isinstance(val, dict) and part in val:
                val = val[part]
            else:
                return m.group(0)
        return str(val)

    return _TEMPLATE_RE.sub(repl, template or "")


def _as_float(s: str) -> float:
    try:
        return float(str(s).strip())
    except (TypeError, ValueError):
        return 0.0


def _safe_json(value: Any) -> dict[str, Any]:
    """Coerce a context/result into a JSON-serialisable dict."""
    if not isinstance(value, dict):
        return {"value": str(value)}
    out: dict[str, Any] = {}
    for k, v in value.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        elif isinstance(v, (list, dict)):
            out[k] = v
        else:
            out[k] = str(v)
    return out

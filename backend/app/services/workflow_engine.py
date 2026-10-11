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
* ``delay``         — bounded wait
* ``webhook``       — outbound HTTP POST (http/https only)

Each step also supports ``retry`` (extra attempts) and
``continue_on_error`` (don't fail the whole run) in its config.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent
from app.database.models.workflow import (
    RunStatus,
    RunStepStatus,
    StepType,
    Workflow,
    WorkflowRun,
    WorkflowRunStep,
)
from app.database.session import AsyncSessionLocal, init_engine
from app.middleware.org_context import OrgContext
from app.providers import DEFAULT_MODEL, get_provider
from app.providers.base import AIProviderError, ChatMessage
from app.services import rag_service
from app.services.agent_runtime import AgentRuntime
from app.services.audit import audit

log = logging.getLogger("app.workflow")

_MAX_DELAY_SECONDS = 60
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
    run, workflow, steps = await _load(session, run_id)
    if run is None:
        log.warning("workflow run %s not found", run_id)
        return
    if workflow is None:
        await _mark_run_failed(session, run_id, "Workflow no longer exists.")
        return

    run.status = RunStatus.running
    run.started_at = _utcnow()
    await session.commit()

    context: dict[str, Any] = dict(run.input or {})
    context.setdefault(
        "trigger", run.trigger.value if hasattr(run.trigger, "value") else str(run.trigger)
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
        astep.output = {"decision": "rejected", "note": note, "text": "Rejected by reviewer."}
        astep.finished_at = _utcnow()
        run.status = RunStatus.cancelled
        run.error_message = ("Rejected at approval step." + (f" {note}" if note else ""))[:2000]
        run.finished_at = _utcnow()
        workflow.run_count += 1
        workflow.last_run_at = run.finished_at
        await session.commit()
        _audit_run(workflow, run)
        return

    astep.status = RunStepStatus.completed
    astep.output = {"decision": "approved", "note": note, "text": "Approved by reviewer."}
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
    failed = False
    error_message: Optional[str] = None

    for rstep in steps[start_index:]:
        stype = rstep.type.value if hasattr(rstep.type, "value") else str(rstep.type)
        cfg = dict(rstep.config or {})

        # Human-approval step: pause the run and persist context for resume.
        if stype == StepType.approval.value:
            rstep.status = RunStepStatus.awaiting_approval
            rstep.started_at = _utcnow()
            rstep.input = _safe_json(context)
            rstep.output = {
                "prompt": _render(str(cfg.get("message", "Approval required.")), context),
                "text": _render(str(cfg.get("message", "Approval required.")), context),
            }
            run.status = RunStatus.awaiting_approval
            run.output = _safe_json(context)  # checkpoint for resume
            await session.commit()
            _audit_run(workflow, run, extra={"paused": True})
            return

        rstep.status = RunStepStatus.running
        rstep.started_at = _utcnow()
        rstep.input = _safe_json(context)
        await session.commit()

        attempts = 1 + min(max(int(cfg.get("retry", 0) or 0), 0), _MAX_RETRIES)
        retry_delay = min(max(int(cfg.get("retry_delay", 2) or 0), 0), _MAX_RETRY_DELAY)
        output: Optional[dict[str, Any]] = None
        last_exc: Optional[Exception] = None

        for attempt in range(attempts):
            try:
                output = await _run_step(session, workflow, rstep, context)
                last_exc = None
                break
            except Exception as exc:  # noqa: BLE001 - recorded per step
                last_exc = exc
                log.warning(
                    "step %s attempt %d/%d failed: %s",
                    rstep.name, attempt + 1, attempts, exc,
                )
                if attempt < attempts - 1 and retry_delay:
                    await asyncio.sleep(retry_delay)

        if last_exc is not None:
            rstep.status = RunStepStatus.failed
            rstep.error_message = str(last_exc)[:2000]
            rstep.finished_at = _utcnow()
            if cfg.get("continue_on_error"):
                await session.commit()
                continue
            failed = True
            error_message = str(last_exc)[:2000]
            await session.commit()
            break

        rstep.output = _safe_json(output or {})
        rstep.status = RunStepStatus.completed
        rstep.finished_at = _utcnow()
        run.steps_completed += 1

        # A condition step may request an early, successful stop.
        if (output or {}).get("_stop"):
            await session.commit()
            break
        await session.commit()

    await _finalize(session, workflow, run, context, failed=failed, error=error_message)


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


def _audit_run(workflow: Workflow, run: WorkflowRun, *, extra: Optional[dict] = None) -> None:
    meta = {"run_id": str(run.id), "status": run.status.value, "steps": run.steps_completed}
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


async def _mark_run_failed(session: AsyncSession, run_id: uuid.UUID, message: str) -> None:
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
) -> dict[str, Any]:
    cfg = dict(rstep.config or {})
    stype = rstep.type.value if hasattr(rstep.type, "value") else str(rstep.type)

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
        return _step_condition(cfg, context)
    if stype == StepType.notification.value:
        return _step_notification(workflow, cfg, context)
    if stype == StepType.delay.value:
        return await _step_delay(cfg)
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
    return {"text": json.dumps(data, ensure_ascii=False), "data": data, "output_var": out_var}


async def _step_ai_summarize(
    workflow: Workflow, cfg: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    text_in = _render(str(cfg.get("input", cfg.get("text", ""))), context).strip()
    if not text_in:
        raise ValueError("ai_summarize step requires 'input' text.")
    max_words = int(cfg.get("max_words", 120) or 120)
    system = f"Summarise the text in at most {max_words} words. Be faithful and concise."
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
            "positive" if "positive" in low
            else "negative" if "negative" in low
            else "neutral"
        )
    out_var = str(cfg.get("output_var") or "sentiment")
    context[out_var] = sentiment
    return {"text": sentiment, "sentiment": sentiment, "score": parsed.get("score"), "output_var": out_var}


async def _step_ai_translate(
    workflow: Workflow, cfg: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    text_in = _render(str(cfg.get("input", cfg.get("text", ""))), context).strip()
    if not text_in:
        raise ValueError("ai_translate step requires 'input' text.")
    target = _render(str(cfg.get("target_language", "English")), context).strip() or "English"
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
    kb_ids_raw = cfg.get("knowledge_base_ids") or []
    kb_ids: Optional[list[uuid.UUID]] = None
    if kb_ids_raw:
        kb_ids = [uuid.UUID(str(k)) for k in kb_ids_raw]
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
        "sources": [
            {"document": c.document_name, "score": c.score} for c in chunks
        ],
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
    if agent is None or agent.organization_id != workflow.organization_id or agent.deleted_at is not None:
        raise ValueError("Agent not found in this organization.")

    message = _render(str(cfg.get("message", "")), context).strip()
    if not message:
        raise ValueError("agent_run step requires a 'message'.")

    ctx = OrgContext(
        user_id=workflow.created_by or uuid.uuid4(),
        cognito_sub="workflow",
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


def _step_condition(cfg: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    left = _render(str(cfg.get("left", "")), context)
    right = _render(str(cfg.get("right", "")), context)
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
    return {"passed": ok, "_stop": stop, "op": op, "left": left, "right": right}


def _step_notification(
    workflow: Workflow, cfg: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    channel = str(cfg.get("channel", "log"))
    message = _render(str(cfg.get("message", "")), context)[:_MAX_OUTPUT_CHARS]
    log.info("WORKFLOW NOTIFY org=%s channel=%s :: %s", workflow.organization_id, channel, message)
    return {"channel": channel, "message": message, "text": message, "delivered": True}


async def _step_delay(cfg: dict[str, Any]) -> dict[str, Any]:
    seconds = min(max(int(cfg.get("seconds", 0)), 0), _MAX_DELAY_SECONDS)
    if seconds:
        await asyncio.sleep(seconds)
    return {"waited_seconds": seconds}


async def _step_webhook(cfg: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    url = _render(str(cfg.get("url", "")), context).strip()
    if not url or not url.lower().startswith(("http://", "https://")):
        raise ValueError("webhook step requires an http(s) 'url'.")
    payload = cfg.get("payload")
    if isinstance(payload, str):
        payload = {"text": _render(payload, context)}
    elif isinstance(payload, dict):
        payload = {k: _render(str(v), context) if isinstance(v, str) else v for k, v in payload.items()}
    else:
        payload = {"context": _safe_json(context)}

    import httpx

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload)
    return {"status_code": resp.status_code, "ok": resp.is_success, "text": f"HTTP {resp.status_code}"}


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

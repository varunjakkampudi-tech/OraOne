"""External programmatic API — ``/api/v1`` (R7 Developer Platform).

Authenticated with org-scoped API keys (``Authorization: Bearer sk_ora_…``
or ``X-API-Key: sk_ora_…``), not Cognito JWTs. Every request:

1. resolves + verifies the key,
2. enforces the plan's per-minute rate limit (and records monthly usage),
3. checks the endpoint's required scope.

The surface mirrors the in-app capabilities — chat/RAG, knowledge bases,
documents, websites, search, workflows, widgets, integrations and analytics —
so external developers can build on every OraOne capability programmatically.

Cross-cutting concerns:
* **Idempotency** — mutating ``POST`` endpoints honour an ``Idempotency-Key``
  header (best-effort, in-process replay within a short TTL).
* **Request logging** — handled centrally by the access-log middleware which
  reads ``request.state.api_ctx`` set here.
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent, AgentStatus
from app.database.models.api_key import ApiKey
from app.database.models.conversation import Conversation, ConversationChannel, ConversationStatus
from app.database.models.document import Document
from app.database.models.integration import Integration
from app.database.models.knowledge_base import KnowledgeBase
from app.database.models.message import Message, MessageSender
from app.database.models.webhook import WebhookEventType
from app.database.models.website import Website
from app.database.models.widget import Widget
from app.database.models.workflow import (
    RunStatus,
    Workflow,
    WorkflowRun,
    WorkflowRunStep,
    WorkflowStep,
    WorkflowTrigger,
)
from app.database.session import get_db
from app.services import analytics_service, api_key_service, usage_service, webhook_service, webhook_outbox
from app.services.rag_answer import answer_query
from app.services.workflow_engine import execute_run
from app.core.model_catalogue import cost_for

router = APIRouter(prefix="/api/v1", tags=["public-api"])


# ── auth plumbing ────────────────────────────────────────────────────────────
def _extract_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            return token
    header_key = request.headers.get("x-api-key")
    if header_key:
        return header_key.strip()
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing API key. Provide 'Authorization: Bearer <key>' or 'X-API-Key'.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_api_key_context(
    request: Request, session: AsyncSession = Depends(get_db)
) -> ApiKey:
    """Authenticate, rate-limit, and stamp last-used for an API key request."""
    raw = _extract_key(request)
    key = await api_key_service.authenticate(session, raw)
    await api_key_service.enforce_rate_limit(session, key)
    await api_key_service.touch_last_used(session, key)
    # Expose context for the access-log middleware.
    request.state.api_ctx = {
        "organization_id": key.organization_id,
        "api_key_id": key.id,
        "key_prefix": key.prefix,
    }
    return key


def require_api_scope(scope: str):
    async def _dep(key: ApiKey = Depends(get_api_key_context)) -> ApiKey:
        api_key_service.require_scope(key, scope)
        return key

    return _dep


# ── idempotency (best-effort, in-process) ────────────────────────────────────
_IDEMPOTENCY: dict[str, tuple[float, dict]] = {}
_IDEMPOTENCY_TTL = 600.0  # 10 minutes


def _idem_lookup(request: Request, organization_id: uuid.UUID) -> tuple[Optional[str], Optional[dict]]:
    key = request.headers.get("idempotency-key")
    if not key:
        return None, None
    composite = f"{organization_id}:{request.url.path}:{key}"
    now = time.time()
    for k in [k for k, (ts, _) in _IDEMPOTENCY.items() if now - ts > _IDEMPOTENCY_TTL]:
        _IDEMPOTENCY.pop(k, None)
    hit = _IDEMPOTENCY.get(composite)
    if hit and now - hit[0] <= _IDEMPOTENCY_TTL:
        return composite, hit[1]
    return composite, None


def _idem_store(composite: Optional[str], payload: dict) -> None:
    if composite:
        _IDEMPOTENCY[composite] = (time.time(), payload)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


# ── request bodies ───────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    knowledge_base_ids: Optional[list[uuid.UUID]] = None
    agent_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    top_k: int = Field(5, ge=1, le=20)
    model: Optional[str] = None
    temperature: float = Field(0.2, ge=0.0, le=1.0)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    knowledge_base_ids: Optional[list[uuid.UUID]] = None
    top_k: int = Field(8, ge=1, le=50)
    source_types: Optional[list[str]] = None


class WorkflowRunRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


# ── meta ─────────────────────────────────────────────────────────────────────
@router.get("/ping")
async def ping(key: ApiKey = Depends(get_api_key_context)) -> dict:
    return {
        "ok": True,
        "organization_id": str(key.organization_id),
        "key_prefix": key.prefix,
        "scopes": key.scopes,
    }


# ── agents ───────────────────────────────────────────────────────────────────
@router.get("/agents")
async def list_agents_v1(
    limit: int = Query(50, ge=1, le=200),
    key: ApiKey = Depends(require_api_scope("agents:read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    rows = await session.scalars(
        select(Agent)
        .where(Agent.organization_id == key.organization_id, Agent.deleted_at.is_(None))
        .order_by(Agent.created_at.desc())
        .limit(limit)
    )
    data = [
        {
            "id": str(a.id),
            "name": a.name,
            "description": a.description,
            "type": a.type.value if a.type else None,
            "status": a.status.value if a.status else None,
            "model": a.model,
            "created_at": _iso(a.created_at),
        }
        for a in rows
    ]
    return {"object": "list", "count": len(data), "data": data}


# ── chat / RAG ───────────────────────────────────────────────────────────────
async def _resolve_agent(
    session: AsyncSession, organization_id: uuid.UUID, agent_id: Optional[uuid.UUID]
) -> Optional[Agent]:
    if agent_id is not None:
        agent = await session.get(Agent, agent_id)
        if agent and agent.organization_id == organization_id and agent.deleted_at is None:
            return agent
        return None
    row = await session.scalars(
        select(Agent)
        .where(
            Agent.organization_id == organization_id,
            Agent.deleted_at.is_(None),
            Agent.status == AgentStatus.active,
        )
        .order_by(Agent.created_at.asc())
        .limit(1)
    )
    return row.first()


def _estimate_tokens(*texts: str) -> int:
    return max(1, sum(len(t or "") for t in texts) // 4)


@router.post("/chat")
async def chat_v1(
    payload: ChatRequest,
    request: Request,
    key: ApiKey = Depends(require_api_scope("chat:write")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    composite, cached = _idem_lookup(request, key.organization_id)
    if cached is not None:
        return cached

    result = await answer_query(
        session,
        payload.message,
        key.organization_id,
        knowledge_base_ids=payload.knowledge_base_ids,
        top_k=payload.top_k,
        model=payload.model,
        temperature=payload.temperature,
    )

    conversation_id: Optional[str] = None
    agent = await _resolve_agent(session, key.organization_id, payload.agent_id)
    if agent is not None:
        conversation: Optional[Conversation] = None
        is_new = False
        if payload.conversation_id is not None:
            conversation = await session.get(Conversation, payload.conversation_id)
            if conversation is not None and conversation.organization_id != key.organization_id:
                conversation = None
        if conversation is None:
            conversation = Conversation(
                organization_id=key.organization_id,
                agent_id=agent.id,
                channel=ConversationChannel.chat,
                status=ConversationStatus.active,
                title=payload.message[:120],
                started_at=_now(),
                last_message_at=_now(),
                extra={"source": "api", "key_prefix": key.prefix},
            )
            session.add(conversation)
            await session.flush()
            is_new = True

        user_msg = Message(
            conversation_id=conversation.id,
            sender=MessageSender.customer,
            message=payload.message,
            token_count=_estimate_tokens(payload.message),
        )
        # Per-message observability — model, token split, indicative cost,
        # latency, and the citations the answer was grounded on.
        prompt_tokens = int(result.get("prompt_tokens") or 0)
        completion_tokens = int(result.get("completion_tokens") or 0)
        total_tokens = int(result.get("total_tokens") or 0) or (prompt_tokens + completion_tokens)
        used_model = result.get("model")
        msg_cost = cost_for(used_model, prompt_tokens, completion_tokens)
        latency_ms = int(result.get("latency_ms") or 0)
        citations = result.get("sources", []) or []
        agent_msg = Message(
            conversation_id=conversation.id,
            sender=MessageSender.agent,
            message=result.get("answer", ""),
            token_count=total_tokens or _estimate_tokens(result.get("answer", "")),
            metadata_={
                "sources": citations,
                "citations": citations,
                "confidence": result.get("confidence"),
                "grounded": result.get("grounded"),
                "context_chunks": result.get("context_chunks"),
                "model": used_model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": msg_cost,
                "latency_ms": latency_ms,
            },
        )
        session.add_all([user_msg, agent_msg])
        conversation.last_message_at = _now()
        # Roll observability up to the conversation so list views stay cheap.
        usage_roll = dict(conversation.extra.get("usage", {})) if isinstance(conversation.extra, dict) else {}
        models_seen = list(usage_roll.get("models", []))
        if used_model and used_model not in models_seen:
            models_seen.append(used_model)
        conv_extra = dict(conversation.extra) if isinstance(conversation.extra, dict) else {}
        conv_extra["usage"] = {
            "message_count": int(usage_roll.get("message_count", 0)) + 2,
            "total_tokens": int(usage_roll.get("total_tokens", 0)) + (user_msg.token_count or 0) + total_tokens,
            "total_cost_usd": round(float(usage_roll.get("total_cost_usd", 0.0)) + msg_cost, 6),
            "last_latency_ms": latency_ms,
            "models": models_seen,
            "last_model": used_model,
        }
        conversation.extra = conv_extra
        conversation_id = str(conversation.id)

        # Transactional outbox: enqueue in the SAME transaction as the
        # business data above, so "commit succeeded" and "webhook will be
        # delivered" are one atomic fact — no fire-and-forget task that a
        # process crash could silently lose (see app/services/webhook_outbox.py).
        if is_new:
            webhook_outbox.enqueue(
                session,
                organization_id=key.organization_id,
                event=WebhookEventType.CONVERSATION_CREATED,
                data={"conversation_id": conversation_id, "agent_id": str(agent.id), "channel": "chat"},
            )
        webhook_outbox.enqueue(
            session,
            organization_id=key.organization_id,
            event=WebhookEventType.MESSAGE_CREATED,
            data={"conversation_id": conversation_id, "message": payload.message[:500]},
        )
        await session.commit()

    response = {
        "object": "chat.completion",
        "conversation_id": conversation_id,
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", 0.0),
        "related_questions": result.get("related_questions", []),
        "grounded": result.get("grounded", False),
        "model": result.get("model"),
        "usage": {
            "prompt_tokens": int(result.get("prompt_tokens") or 0),
            "completion_tokens": int(result.get("completion_tokens") or 0),
            "total_tokens": int(result.get("total_tokens") or 0),
            "cost_usd": cost_for(
                result.get("model"),
                int(result.get("prompt_tokens") or 0),
                int(result.get("completion_tokens") or 0),
            ),
            "latency_ms": int(result.get("latency_ms") or 0),
        },
    }
    _idem_store(composite, response)
    return response


@router.get("/conversations")
async def list_conversations_v1(
    limit: int = Query(50, ge=1, le=200),
    key: ApiKey = Depends(require_api_scope("chat:read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    rows = await session.scalars(
        select(Conversation)
        .where(Conversation.organization_id == key.organization_id, Conversation.deleted_at.is_(None))
        .order_by(Conversation.started_at.desc())
        .limit(limit)
    )
    data = [
        {
            "id": str(c.id),
            "agent_id": str(c.agent_id) if c.agent_id else None,
            "channel": c.channel.value if c.channel else None,
            "status": c.status.value if c.status else None,
            "title": c.title,
            "started_at": _iso(c.started_at),
            "last_message_at": _iso(c.last_message_at),
        }
        for c in rows
    ]
    return {"object": "list", "count": len(data), "data": data}


@router.get("/conversations/{conversation_id}")
async def get_conversation_v1(
    conversation_id: uuid.UUID,
    key: ApiKey = Depends(require_api_scope("chat:read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    conv = await session.get(Conversation, conversation_id)
    if conv is None or conv.organization_id != key.organization_id or conv.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    msgs = await session.scalars(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at.asc())
    )
    return {
        "id": str(conv.id),
        "agent_id": str(conv.agent_id) if conv.agent_id else None,
        "channel": conv.channel.value if conv.channel else None,
        "status": conv.status.value if conv.status else None,
        "title": conv.title,
        "started_at": _iso(conv.started_at),
        "messages": [
            {
                "id": str(m.id),
                "sender": m.sender.value if m.sender else None,
                "message": m.message,
                "token_count": m.token_count,
                "created_at": _iso(m.created_at),
            }
            for m in msgs
        ],
    }


# ── knowledge bases ──────────────────────────────────────────────────────────
@router.get("/knowledge-bases")
async def list_kbs_v1(
    limit: int = Query(50, ge=1, le=200),
    key: ApiKey = Depends(require_api_scope("knowledge:read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    rows = await session.scalars(
        select(KnowledgeBase)
        .where(KnowledgeBase.organization_id == key.organization_id, KnowledgeBase.deleted_at.is_(None))
        .order_by(KnowledgeBase.created_at.desc())
        .limit(limit)
    )
    data = [
        {
            "id": str(k.id),
            "name": k.name,
            "description": k.description,
            "status": k.status.value if k.status else None,
            "created_at": _iso(k.created_at),
        }
        for k in rows
    ]
    return {"object": "list", "count": len(data), "data": data}


# ── documents ────────────────────────────────────────────────────────────────
@router.get("/documents")
async def list_documents_v1(
    knowledge_base_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    key: ApiKey = Depends(require_api_scope("documents:read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    stmt = select(Document).where(
        Document.organization_id == key.organization_id, Document.deleted_at.is_(None)
    )
    if knowledge_base_id is not None:
        stmt = stmt.where(Document.knowledge_base_id == knowledge_base_id)
    rows = await session.scalars(stmt.order_by(Document.created_at.desc()).limit(limit))
    data = [
        {
            "id": str(d.id),
            "knowledge_base_id": str(d.knowledge_base_id),
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "status": d.status.value if d.status else None,
            "source": d.source,
            "created_at": _iso(d.created_at),
        }
        for d in rows
    ]
    return {"object": "list", "count": len(data), "data": data}


# ── websites ─────────────────────────────────────────────────────────────────
@router.get("/websites")
async def list_websites_v1(
    limit: int = Query(50, ge=1, le=200),
    key: ApiKey = Depends(require_api_scope("websites:read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    rows = await session.scalars(
        select(Website)
        .where(Website.organization_id == key.organization_id, Website.deleted_at.is_(None))
        .order_by(Website.created_at.desc())
        .limit(limit)
    )
    data = [
        {
            "id": str(w.id),
            "name": w.name,
            "base_url": w.base_url,
            "status": w.status,
            "pages_count": w.pages_count,
            "last_crawled_at": _iso(w.last_crawled_at),
            "created_at": _iso(w.created_at),
        }
        for w in rows
    ]
    return {"object": "list", "count": len(data), "data": data}


# ── search ───────────────────────────────────────────────────────────────────
@router.post("/search")
async def search_v1(
    payload: SearchRequest,
    request: Request,
    key: ApiKey = Depends(require_api_scope("search:read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from app.services import rag_service

    chunks = await rag_service.hybrid_search(
        session,
        payload.query,
        key.organization_id,
        knowledge_base_ids=payload.knowledge_base_ids,
        top_k=payload.top_k,
        source_types=payload.source_types,
    )
    sources = rag_service.dedupe_sources(chunks)
    return {
        "object": "search.results",
        "query": payload.query,
        "count": len(sources),
        "confidence": rag_service.compute_confidence(chunks, payload.query),
        "results": sources,
    }


# ── workflows ────────────────────────────────────────────────────────────────
@router.get("/workflows")
async def list_workflows_v1(
    limit: int = Query(50, ge=1, le=200),
    key: ApiKey = Depends(require_api_scope("workflows:read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    rows = await session.scalars(
        select(Workflow)
        .where(Workflow.organization_id == key.organization_id, Workflow.deleted_at.is_(None))
        .order_by(Workflow.created_at.desc())
        .limit(limit)
    )
    data = [
        {
            "id": str(w.id),
            "name": w.name,
            "description": w.description,
            "status": w.status.value if w.status else None,
            "run_count": w.run_count,
            "success_count": w.success_count,
            "last_run_at": _iso(w.last_run_at),
        }
        for w in rows
    ]
    return {"object": "list", "count": len(data), "data": data}


@router.post("/workflows/{workflow_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_workflow_v1(
    workflow_id: uuid.UUID,
    payload: WorkflowRunRequest,
    request: Request,
    background: BackgroundTasks,
    key: ApiKey = Depends(require_api_scope("workflows:execute")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    composite, cached = _idem_lookup(request, key.organization_id)
    if cached is not None:
        return cached

    workflow = await session.get(Workflow, workflow_id)
    if workflow is None or workflow.organization_id != key.organization_id or workflow.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
    steps = list(
        await session.scalars(
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == workflow.id)
            .order_by(WorkflowStep.order_index.asc())
        )
    )
    if not steps:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workflow has no steps.")

    trigger = getattr(WorkflowTrigger, "api", WorkflowTrigger.manual)
    run = WorkflowRun(
        workflow_id=workflow.id,
        organization_id=key.organization_id,
        status=RunStatus.queued,
        trigger=trigger,
        input=payload.input or {},
        steps_total=len(steps),
    )
    session.add(run)
    await session.flush()
    for step in steps:
        session.add(
            WorkflowRunStep(
                run_id=run.id,
                organization_id=key.organization_id,
                step_id=step.id,
                order_index=step.order_index,
                type=step.type,
                name=step.name,
                config=step.config or {},
            )
        )
    await session.commit()
    background.add_task(execute_run, run.id)

    response = {"object": "workflow.run", "run_id": str(run.id), "status": "queued"}
    _idem_store(composite, response)
    return response


# ── widgets ──────────────────────────────────────────────────────────────────
@router.get("/widgets")
async def list_widgets_v1(
    limit: int = Query(50, ge=1, le=200),
    key: ApiKey = Depends(require_api_scope("widgets:read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    rows = await session.scalars(
        select(Widget)
        .where(Widget.organization_id == key.organization_id, Widget.deleted_at.is_(None))
        .order_by(Widget.created_at.desc())
        .limit(limit)
    )
    data = [
        {
            "id": str(w.id),
            "name": w.name,
            "public_key": w.public_key,
            "status": w.status,
            "widget_type": w.widget_type,
            "agent_id": str(w.agent_id) if w.agent_id else None,
            "published_at": _iso(w.published_at),
        }
        for w in rows
    ]
    return {"object": "list", "count": len(data), "data": data}


# ── integrations ─────────────────────────────────────────────────────────────
@router.get("/integrations")
async def list_integrations_v1(
    limit: int = Query(50, ge=1, le=200),
    key: ApiKey = Depends(require_api_scope("integrations:read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    rows = await session.scalars(
        select(Integration)
        .where(Integration.organization_id == key.organization_id, Integration.deleted_at.is_(None))
        .order_by(Integration.created_at.desc())
        .limit(limit)
    )
    data = [
        {
            "id": str(i.id),
            "provider": i.provider,
            "category": i.category,
            "type": i.type.value if i.type else None,
            "status": i.status.value if i.status else None,
            "external_account": i.external_account,
            "last_synced_at": _iso(i.last_synced_at),
        }
        for i in rows
    ]
    return {"object": "list", "count": len(data), "data": data}


# ── usage & analytics ────────────────────────────────────────────────────────
@router.get("/usage")
async def usage_v1(
    key: ApiKey = Depends(require_api_scope("usage:read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await usage_service.usage_snapshot(session, key.organization_id)


@router.get("/analytics/overview")
async def analytics_v1(
    days: int = Query(30, ge=1, le=90),
    key: ApiKey = Depends(require_api_scope("analytics:read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await analytics_service.org_overview(session, key.organization_id, days)


@router.get("/analytics/{module}")
async def analytics_module_v1(
    module: str,
    days: int = Query(30, ge=1, le=90),
    key: ApiKey = Depends(require_api_scope("analytics:read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    fn = analytics_service.MODULE_FUNCTIONS.get(module)
    if fn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown analytics module '{module}'.",
        )
    return await fn(session, key.organization_id, days)

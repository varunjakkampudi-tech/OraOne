from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
# Explicit process/container environment wins over the local convenience file.
# This is required for Compose/Hostinger secret injection and safe overrides.
load_dotenv(ROOT_DIR / ".env", override=False)

from app.core.logging import configure_logging  # noqa: E402

configure_logging()

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

# Self-hosted auth router (Argon2 + JWT — see app/services/auth_service.py)
from app.api.auth.routes import router as auth_router
from app.api.contact import register_contact_routes
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization


# Business profile
class BusinessProfileIn(BaseModel):
    company_name: str
    industry: str
    phone: Optional[str] = None
    website: Optional[str] = None
    email: Optional[EmailStr] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Best-effort startup/shutdown. Every step is guarded so a degraded
    dependency never blocks boot; on shutdown, background loops are stopped
    before the engine they depend on is disposed."""
    log = logging.getLogger(__name__)
    # ── startup ──
    # Production-like environments refuse to boot with incomplete provider config.
    from app.core.startup_checks import validate_startup_configuration

    validate_startup_configuration()
    # Initialise the Postgres async engine lazily — won't crash boot if the DB
    # is unreachable (e.g. private VPC). Routes that need it fail individually.
    try:
        from app.database.session import init_engine

        init_engine()
        log.info("Postgres engine initialised.")
    except Exception as e:
        log.warning(f"Postgres engine not initialised (will retry on first use): {e}")
    # Background loops run in the dedicated `worker.py` process in production.
    # Keeping them opt-in here prevents duplicate schedulers under Gunicorn.
    if os.environ.get("RUN_BACKGROUND_WORKERS", "false").strip().lower() == "true":
        try:
            from app.services.workflow_scheduler import start_scheduler

            start_scheduler()
            from app.services.webhook_outbox import start_outbox_worker

            start_outbox_worker()
        except Exception as e:
            log.warning(f"Background workers not started: {e}")
    # OpenTelemetry tracing — no-op unless OTEL_EXPORTER_OTLP_ENDPOINT is set.
    try:
        from app.core.tracing import configure_tracing

        configure_tracing(app)
    except Exception as e:
        log.warning(f"Tracing not configured: {e}")
    # Phase 12 — seed the billing plan catalogue (best-effort, idempotent).
    try:
        from app.database.session import AsyncSessionLocal
        from app.services.billing_service import ensure_plans_seeded

        if AsyncSessionLocal is not None:
            async with AsyncSessionLocal() as _s:
                await ensure_plans_seeded(_s)
    except Exception as e:
        log.warning(f"Plan seeding skipped: {e}")
    # Auth (signup/login/refresh/logout) is self-hosted — see app/api/auth/routes.py.

    yield

    # ── shutdown ──
    # Stop background loops before disposing the engine they depend on —
    # otherwise a mid-tick task can race a closed connection pool during
    # shutdown, and a crash-only exit (no cancel) leaves whatever it was
    # doing (e.g. an outbox row claimed PROCESSING) to be reclaimed later
    # by the stale-PROCESSING sweep on the next process's first tick.
    if os.environ.get("RUN_BACKGROUND_WORKERS", "false").strip().lower() == "true":
        try:
            from app.services.workflow_scheduler import stop_scheduler

            await stop_scheduler()
        except Exception:
            pass
        try:
            from app.services.webhook_outbox import stop_outbox_worker

            await stop_outbox_worker()
        except Exception:
            pass
    try:
        from app.database.session import dispose_engine

        await dispose_engine()
    except Exception:
        pass


# ---------- App ----------
app = FastAPI(title="OraOne API", version="2.0.0", lifespan=lifespan)
api = APIRouter(prefix="/api")


@api.get("/")
async def root():
    return {"message": "OraOne API v1", "tagline": "One AI. Every Conversation."}


@api.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


# ---------- Auth endpoints ----------
# Self-hosted auth (Argon2 + JWT) — see app/services/auth_service.py.
# All /api/auth/* endpoints are mounted from auth_router at the bottom of
# this file (signup, verify, resend, login, refresh, forgot-password,
# reset-password, logout, me, identity).


# ---------- Onboarding ----------
@api.post("/onboarding/complete")
async def complete_onboarding(
    payload: BusinessProfileIn,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm.attributes import flag_modified

    from app.database.models.organization import Organization

    org = await session.get(Organization, ctx.organization_id)
    if org is None:
        raise HTTPException(
            status_code=404, detail="No workspace found for this account."
        )

    org.settings = {
        **(org.settings or {}),
        "onboarding": {
            "onboarded": True,
            "company_name": payload.company_name,
            "industry": payload.industry,
            "phone": payload.phone,
            "website": payload.website,
            "business_email": payload.email,
        },
    }
    flag_modified(org, "settings")
    await session.commit()
    return {"message": "Onboarding complete"}


# ---------- Agents ----------
# Agent CRUD has moved to /app/backend/app/api/agents/routes.py (Phase 6).
# The new routes are Postgres-backed, org-scoped (Phase 5), soft-deletable,
# paginated, searchable, filterable, and audit-logged. The router is mounted
# below alongside the other v2 surfaces.


# ---------- Leads ----------
# Legacy Mongo-backed /leads endpoints have been removed. Leads (CRM) are now
# served by the Postgres-backed, project-scoped router mounted below
# (app/api/leads/routes.py) — GET/POST/PATCH/DELETE /api/leads + /api/leads/stats.


# ---------- Contact (marketing) ----------
register_contact_routes(api, get_db)


# ---------- Mount + middleware ----------
app.include_router(api)
# Postgres health probe (separate router, no auth)
from app.api.health import router as health_router  # noqa: E402

app.include_router(health_router)
# Self-hosted authentication (Argon2 + JWT)
app.include_router(auth_router)
# Projects — workspace hierarchy (Organization → Project → resources)
from app.api.projects import router as projects_router  # noqa: E402

app.include_router(projects_router)
# Phase 5 — tenant-scoped business API (Postgres-backed)
from app.api.v2 import router as v2_router  # noqa: E402

app.include_router(v2_router)
# Phase 6 — full Agent CRUD (Postgres-backed)
from app.api.agents import router as agents_router  # noqa: E402

app.include_router(agents_router)
# Knowledge base foundation (PostgreSQL + local file storage)
from app.api.knowledge import router as knowledge_router  # noqa: E402

app.include_router(knowledge_router)
# R2 — Enterprise Knowledge: folders, search, preview, versions, bulk actions
from app.api.knowledge import knowledge_org_router  # noqa: E402

app.include_router(knowledge_org_router)

from app.api.knowledge import knowledge_sources_router  # noqa: E402

app.include_router(knowledge_sources_router)
# Phase 8 — AI Chat & Agent Runtime (conversations, messages, SSE streaming)
from app.api.chat import router as chat_router  # noqa: E402

app.include_router(chat_router)
# R1 — Enterprise Chat: folders + public share view
from app.api.chat import folders_router as chat_folders_router  # noqa: E402
from app.api.chat import public_chat_router  # noqa: E402

app.include_router(chat_folders_router)
app.include_router(public_chat_router)
# Phase 10 — Integrations Platform (connect external apps → sync into KB)
from app.api.integrations import router as integrations_router  # noqa: E402

app.include_router(integrations_router)
# Phase 11 — Workflow Automation (chain AI + KB + agents into automations)
from app.api.workflows import router as workflows_router  # noqa: E402

app.include_router(workflows_router)
# Phase 12 — Enterprise SaaS: Billing & Subscriptions (Module 1)
from app.api.billing import router as billing_router  # noqa: E402

app.include_router(billing_router)
# Phase 12 — Enterprise SaaS: RBAC permission matrix (Module 4)
from app.api.rbac import router as rbac_router  # noqa: E402

app.include_router(rbac_router)
# Phase 12 — Enterprise SaaS: Team management (Module 3)
from app.api.team import router as team_router  # noqa: E402

app.include_router(team_router)
# Phase 12 — Enterprise SaaS: Usage metering & quotas (Module 2)
from app.api.usage import router as usage_router  # noqa: E402

app.include_router(usage_router)
# Phase 12 — Enterprise SaaS: Organization analytics (Module 6)
from app.api.analytics import router as analytics_router  # noqa: E402

app.include_router(analytics_router)
# Phase 12 — Enterprise SaaS: API platform — key management (Module 9)
from app.api.api_keys import router as api_keys_router  # noqa: E402

app.include_router(api_keys_router)
# Phase 12 — Enterprise SaaS: External programmatic API /api/v1 (Module 9)
from app.api.public_api import router as public_api_router  # noqa: E402

app.include_router(public_api_router)
# Phase 12 — Enterprise SaaS: AI model router (Module 13)
from app.api.ai_models import router as ai_models_router  # noqa: E402

app.include_router(ai_models_router)
# Phase 12 — Enterprise SaaS: White-label branding (Module 15)
from app.api.branding import router as branding_router  # noqa: E402

app.include_router(branding_router)
# Phase 12 — Enterprise SaaS: Audit log viewer (Module 5)
from app.api.audit import router as audit_router  # noqa: E402

app.include_router(audit_router)
# R3 — Enterprise Website Crawling Engine
from app.api.websites import router as websites_router  # noqa: E402

app.include_router(websites_router)
# R4 — Enterprise RAG Engine (hybrid retrieval + grounded answers)
from app.api.rag import router as rag_router  # noqa: E402

app.include_router(rag_router)
# R6 — Embedded Website Widget (admin CRUD + public domain-restricted chat)
from app.api.widgets import router as widgets_router  # noqa: E402
from app.api.widgets import public_router as widget_public_router  # noqa: E402

app.include_router(widgets_router)
app.include_router(widget_public_router)
# Phase B — Channels & Deploy (Universal Agent: one agent, every channel)
from app.api.channels import router as channels_router  # noqa: E402

app.include_router(channels_router)
# Phase M — Omnichannel inbound (WhatsApp, SMS, Telegram, Email, SDK, …)
from app.api.omnichannel import router as omnichannel_router  # noqa: E402

app.include_router(omnichannel_router)
# Outbound calling queue (campaigns) and the Twilio status callback
from app.api.calls import router as calls_router  # noqa: E402
from app.api.calls import callback_router as calls_callback_router  # noqa: E402

app.include_router(calls_router)
app.include_router(calls_callback_router)
# AI voice agent: inbound calls, speech turns and outbound TwiML
from app.api.voice import router as voice_router  # noqa: E402

app.include_router(voice_router)
# Do-not-contact list (consent and opt-outs used by calls and messages)
from app.api.contact_policy import router as contact_policy_router  # noqa: E402

app.include_router(contact_policy_router)
# R7 — Developer Platform: outbound webhooks (dashboard management)
from app.api.webhooks.routes import router as webhooks_router  # noqa: E402

app.include_router(webhooks_router)
# R9 — Enterprise Team Collaboration (teams, sharing, comments, notifications, …)
from app.api.collaboration import router as collaboration_router  # noqa: E402

app.include_router(collaboration_router)
# R10 — Enterprise Security & Release Readiness (security events, system ops)
from app.api.operations import router as operations_router  # noqa: E402

app.include_router(operations_router)
# Leads (CRM) — first-class lead capture + pipeline (project-scoped)
from app.api.leads import router as leads_router  # noqa: E402
from app.api.escalations import router as escalations_router  # noqa: E402

app.include_router(leads_router)
app.include_router(escalations_router)
from app.api.inbox import router as inbox_router  # noqa: E402

app.include_router(inbox_router)
from app.api.marketing import router as marketing_router  # noqa: E402

app.include_router(marketing_router)
# Feature requests / feedback board (org-scoped) — ideas, bugs, feedback + voting
from app.api.feature_requests import router as feature_requests_router  # noqa: E402

app.include_router(feature_requests_router)

# Phase Z — AI Marketplace
from app.api.marketplace import marketplace_router  # noqa: E402

app.include_router(marketplace_router)

# Bonus — AI assistants (meeting, QA, forecasting, personalization, A/B, copilot)
from app.api.assistants import assistants_router  # noqa: E402

app.include_router(assistants_router)

# Workspace Intelligence — optimization score, knowledge coverage, revenue
# attribution, customer 360, confidence heatmap, conversation simulator (org-scoped)
from app.api.workspace_intel import router as workspace_intel_router  # noqa: E402

app.include_router(workspace_intel_router)

# Phase 1 — Product & feature entitlements (self-service read model)
from app.api.entitlements import router as entitlements_router  # noqa: E402

app.include_router(entitlements_router)

from app.api.agent_versioning import router as agent_versioning_router  # noqa: E402

app.include_router(agent_versioning_router)

# Super Admin Control Center (platform-scoped, founder-only)
from app.api.super_admin import super_admin_router  # noqa: E402

app.include_router(super_admin_router)

# Admin configuration console (super-admin only)
from app.api.admin_config import router as admin_config_router  # noqa: E402

app.include_router(admin_config_router)

# Platform admin analytics (aggregate counts only; super-admin and admin)
from app.api.admin_analytics import router as admin_analytics_router  # noqa: E402

app.include_router(admin_analytics_router)

# Beta feature flags: caller flags (any signed-in user) and super-admin overrides
from app.api.feature_flags import admin_router as admin_feature_flags_router  # noqa: E402
from app.api.feature_flags import router as feature_flags_router  # noqa: E402

app.include_router(feature_flags_router)
app.include_router(admin_feature_flags_router)

# Admin log viewer: error events, related log lines, audited JSON/CSV downloads
from app.api.admin_logs import router as admin_logs_router  # noqa: E402

app.include_router(admin_logs_router)

from app.core.cors import dashboard_origins  # noqa: E402

allow_origins = dashboard_origins()


class WidgetPublicCORSMiddleware:
    """Permissive CORS for the public embeddable widget API only.

    ``/api/widget/*`` is unauthenticated, cookie-free and already guarded at the
    app layer (public key + per-widget domain allow-list), so a customer must be
    able to call it from ANY origin their site is served on. The global
    CORSMiddleware keeps its strict allow-list for the authenticated dashboard
    API. Pure-ASGI + header-only, so it never buffers the SSE stream endpoint.
    """

    WIDGET_PREFIX = "/api/widget"

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if scope.get("type") != "http" or not (
            path == self.WIDGET_PREFIX or path.startswith(self.WIDGET_PREFIX + "/")
        ):
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers") or [])
        origin = headers.get(b"origin")
        if origin is None:
            return await self.app(scope, receive, send)
        if scope.get("method") == "OPTIONS":
            acrh = headers.get(b"access-control-request-headers") or b"*"
            await send(
                {
                    "type": "http.response.start",
                    "status": 204,
                    "headers": [
                        (b"access-control-allow-origin", origin),
                        (b"access-control-allow-methods", b"GET, POST, OPTIONS"),
                        (b"access-control-allow-headers", acrh),
                        (b"access-control-max-age", b"600"),
                        (b"vary", b"Origin"),
                        (b"content-length", b"0"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": b""})
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                hdrs = [
                    (k, v)
                    for (k, v) in message.get("headers", [])
                    if k.lower() != b"access-control-allow-origin"
                ]
                hdrs.append((b"access-control-allow-origin", origin))
                hdrs.append((b"vary", b"Origin"))
                message["headers"] = hdrs
            await send(message)

        await self.app(scope, receive, send_wrapper)


# ---------- Structured error envelope ----------
# Every HTTPException in the codebase raises a bare `detail=` string; this
# handler wraps them all in one consistent shape at the boundary instead of
# touching every one of the ~250 call sites. Handlers/middleware that already
# build their own structured JSONResponse (rate limiting, idempotency) never
# reach this — it only normalises the common case.
from starlette.responses import JSONResponse as _ErrJSONResponse  # noqa: E402

_STATUS_CODE_NAMES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    402: "PAYMENT_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
}


@app.exception_handler(HTTPException)
async def structured_http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        body = detail  # already structured — pass through unchanged
    else:
        code = _STATUS_CODE_NAMES.get(exc.status_code, "ERROR")
        message = detail if isinstance(detail, str) else str(detail)
        body = {
            "success": False,
            "error": {"code": code, "message": message},
            "requestId": getattr(request.state, "request_id", None),
        }
    return _ErrJSONResponse(
        status_code=exc.status_code, content=body, headers=exc.headers or {}
    )


# ---------- Security headers ----------
@app.middleware("http")
async def security_headers_mw(request, call_next):
    response = await call_next(request)
    # Hardening — see https://owasp.org/www-project-secure-headers/
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    )
    response.headers.setdefault("X-XSS-Protection", "0")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    # This is a JSON API (no first-party HTML/JS to inline) — a strict CSP is
    # safe here. Swagger/Redoc under /docs load their own inline assets, so
    # exempt those paths rather than loosen the policy for the whole API.
    if not request.url.path.startswith(("/docs", "/redoc")):
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
    if request.url.scheme == "https":
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload"
        )
    return response


# ---------- Request correlation + structured access log ----------
# Request IDs, the access log and 5xx error capture live in the outermost ASGI
# middleware, installed at the end of this file (app/middleware/request_context.py).
from app.middleware.access_log import request_route_label  # noqa: E402
from app.middleware.upload_size_limit import UploadSizeLimitMiddleware  # noqa: E402


# ---------- Rate limiting (tiered) + idempotency ----------
# See app/middleware/rate_limit.py and app/middleware/idempotency.py — both
# ride on the shared Redis-backed cache (in-process fallback when REDIS_URL
# is unset), so limits/dedup are correct across every worker process.
from app.middleware.rate_limit import rate_limit_middleware as _rate_limit_middleware  # noqa: E402
from app.middleware.idempotency import idempotency_middleware as _idempotency_middleware  # noqa: E402


@app.middleware("http")
async def rate_limit_mw(request, call_next):
    return await _rate_limit_middleware(request, call_next)


@app.middleware("http")
async def idempotency_mw(request, call_next):
    return await _idempotency_middleware(request, call_next)


@app.middleware("http")
async def audit_flush_mw(request, call_next):
    """Persist buffered audit records after each request (best-effort).

    Phase 12 Module 5 — drains ``app.services.audit`` into ``audit_logs``.
    Never blocks or fails the response.
    """
    response = await call_next(request)
    try:
        from app.services.audit import _PENDING, flush_pending

        if _PENDING:
            from app.database.session import AsyncSessionLocal

            if AsyncSessionLocal is not None:
                async with AsyncSessionLocal() as _s:
                    await flush_pending(_s)
    except Exception:  # noqa: BLE001 — auditing must never break a request
        pass
    return response


@app.middleware("http")
async def api_v1_access_log_mw(request, call_next):
    """R7 — record an ``api_request_logs`` row for every ``/api/v1`` call.

    Best-effort: reads ``request.state.api_ctx`` (set by the API-key auth
    dependency) for org/key attribution and never blocks or fails the
    response.
    """
    import time as _time

    is_v1 = request.url.path.startswith("/api/v1")
    start = _time.perf_counter() if is_v1 else 0.0
    response = await call_next(request)
    if not is_v1:
        return response
    try:
        latency_ms = int((_time.perf_counter() - start) * 1000)
        ctx = getattr(request.state, "api_ctx", None)
        if ctx is not None:
            from app.database.models.api_log import ApiRequestLog
            from app.database.session import AsyncSessionLocal

            if AsyncSessionLocal is not None:
                async with AsyncSessionLocal() as _s:
                    _s.add(
                        ApiRequestLog(
                            organization_id=ctx.get("organization_id"),
                            api_key_id=ctx.get("api_key_id"),
                            key_prefix=ctx.get("key_prefix"),
                            method=request.method,
                            # Route template: never store path-borne tokens.
                            endpoint=request_route_label(request)[:255],
                            status_code=response.status_code,
                            latency_ms=latency_ms,
                        )
                    )
                    await _s.commit()
    except Exception:  # noqa: BLE001 — access logging must never break a request
        pass
    return response


# Cookie-authenticated unsafe requests must come from an allow-listed origin.
@app.middleware("http")
async def cookie_origin_mw(request, call_next):
    from app.core.cookies import cookie_origin_refused

    if cookie_origin_refused(
        method=request.method,
        headers=request.headers,
        cookies=request.cookies,
        allowed_origins=allow_origins,
    ):
        return _ErrJSONResponse(
            status_code=403,
            content={
                "success": False,
                "error": {
                    "code": "FORBIDDEN",
                    "message": "Request origin is not allowed for cookie-authenticated changes.",
                },
                "requestId": getattr(request.state, "request_id", None),
            },
        )
    return await call_next(request)


# Upload size precheck sits inside CORS so its 413 still carries CORS headers.
app.add_middleware(UploadSizeLimitMiddleware)

# Register CORS last so it wraps early rate-limit/idempotency responses too.
# The outer widget policy still applies only to domain-checked public routes.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(WidgetPublicCORSMiddleware)

# Outermost: request IDs on every response, one access line per request, and
# scrubbed error_events rows for 5xx responses and unhandled exceptions.
from app.middleware.request_context import install_request_context  # noqa: E402

install_request_context(app)

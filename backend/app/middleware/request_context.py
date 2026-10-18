"""Request correlation, one access-log line per request, and server error capture.

This is a pure ASGI middleware added outermost, so it sees every response,
including the 500 that Starlette would otherwise produce outside the rest of the
stack. For each request it:

* accepts a well-formed ``X-Request-Id`` from the caller, or generates one, and
  returns it on every response (also on unhandled-exception 500s);
* binds the request ID, route template and pseudonymous actor/org hashes to every
  structlog line emitted while the request runs (see ``add_request_context``);
* emits one ``request.completed`` access line with status and duration;
* on a 5xx response or an unhandled exception, records a scrubbed ``error_events``
  row through ``app.services.error_events.record_failure``.

Route templates are used instead of raw paths, so bot tokens and share links
never reach a log line.
"""

from __future__ import annotations

import re
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping, Optional

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.middleware.access_log import route_template

REQUEST_ID_HEADER = b"x-request-id"
_REQUEST_ID_RE = re.compile(r"[A-Za-z0-9._:-]{8,128}")

#: Per-request context for structlog. Holds a reference to the live ASGI scope so
#: the route template is read when a line is written (routing has happened by then).
_CURRENT: ContextVar[Optional[dict[str, Any]]] = ContextVar(
    "request_log_context", default=None
)

_INTERNAL_ERROR_MESSAGE = (
    "An unexpected error occurred. Quote the request ID when contacting support."
)


def safe_request_id(raw: str | None) -> str:
    """Honour a caller's request ID only when it is a short, plain token.

    Anything else (too long, unexpected characters) is replaced, so a caller can
    never inject newlines or markup into the log stream.
    """
    if raw and _REQUEST_ID_RE.fullmatch(raw):
        return raw
    return str(uuid.uuid4())


def add_request_context(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """structlog processor: stamp request correlation fields on every line.

    Fields set explicitly on a call win (``setdefault``), so access and error lines
    can name their own route and status.
    """
    ctx = _CURRENT.get()
    if ctx is None:
        return event_dict
    scope: Mapping[str, Any] = ctx["scope"]
    event_dict.setdefault("request_id", ctx["request_id"])
    event_dict.setdefault("method", scope.get("method"))
    event_dict.setdefault("route", route_template(scope))
    state = scope.get("state") or {}
    for key in ("actor_hash", "org_hash"):
        value = state.get(key)
        if value:
            event_dict.setdefault(key, value)
    return event_dict


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from app.core.logging import access_logger
        from app.core.tracing import current_trace_id

        raw_header = dict(scope.get("headers") or []).get(REQUEST_ID_HEADER)
        request_id = safe_request_id(
            raw_header.decode("latin-1") if raw_header else None
        )
        scope.setdefault("state", {})["request_id"] = request_id

        started_at = time.perf_counter()
        response_state: dict[str, Any] = {"status": None, "started": False}

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_state["status"] = message["status"]
                response_state["started"] = True
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != REQUEST_ID_HEADER
                ]
                headers.append((REQUEST_ID_HEADER, request_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        token = _CURRENT.set({"scope": scope, "request_id": request_id})
        failure: BaseException | None = None
        try:
            try:
                await self.app(scope, receive, send_with_request_id)
            except Exception as exc:  # noqa: BLE001 — converted into a 500 below
                failure = exc
                if response_state["started"]:
                    # Headers already left the server; the connection is unusable.
                    raise
                response_state["status"] = 500
                body = {
                    "success": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": _INTERNAL_ERROR_MESSAGE,
                    },
                    "requestId": request_id,
                }
                await JSONResponse(
                    status_code=500,
                    content=body,
                    headers={"X-Request-Id": request_id},
                )(scope, receive, send)

            status = response_state["status"] or 500
            duration_ms = int((time.perf_counter() - started_at) * 1000)
            access_logger.info(
                "request.completed",
                request_id=request_id,
                trace_id=current_trace_id(),
                method=scope.get("method"),
                route=route_template(scope),
                status_code=status,
                duration_ms=duration_ms,
            )
            if failure is not None or status >= 500:
                await _record(
                    scope,
                    request_id=request_id,
                    status=status,
                    duration_ms=duration_ms,
                    failure=failure,
                    trace_id=current_trace_id(),
                )
        finally:
            _CURRENT.reset(token)


async def _record(
    scope: Scope,
    *,
    request_id: str,
    status: int,
    duration_ms: int,
    failure: BaseException | None,
    trace_id: str | None,
) -> None:
    from app.services.error_events import record_failure

    state = scope.get("state") or {}
    try:
        await record_failure(
            request_id=request_id,
            method=str(scope.get("method") or ""),
            route=route_template(scope),
            status_code=status,
            duration_ms=duration_ms,
            exc=failure,
            raw_path=scope.get("path"),
            trace_id=trace_id,
            actor_hash=state.get("actor_hash"),
            org_hash=state.get("org_hash"),
            occurred_at=_utcnow(),
        )
    except Exception:  # noqa: BLE001 — error capture must never fail a request
        return


def install_request_context(app: Any) -> None:
    """Register the middleware as the outermost layer of ``app``."""
    app.add_middleware(RequestContextMiddleware)

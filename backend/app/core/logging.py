"""Structured logging configuration (structlog).

One JSON log line per request, with a stable schema every log aggregator
(Loki, CloudWatch, Datadog, whatever) can parse without custom parsing
rules: timestamp, level, event, request_id, route, method, status_code,
duration_ms, actor_hash, org_hash. Request fields are stamped by
``app.middleware.request_context.add_request_context``.

When ``APP_LOG_FILE`` is set, the same JSON lines are also appended to that
file (rotated) so the admin log viewer can show a request's related lines.

``configure_logging()`` is idempotent — safe to call multiple times (e.g.
once from server.py, once from a test fixture) without duplicating handlers.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys

import structlog

_configured = False


def _request_context_processor(logger, method_name, event_dict):
    # Imported lazily: the middleware module imports this one for access_logger.
    from app.middleware.request_context import add_request_context

    return add_request_context(logger, method_name, event_dict)


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    # Windows consoles can retain a legacy encoding; diagnostic Unicode must
    # never prevent a log record from being emitted.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="backslashreplace")

    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # JSON in anything that looks like a real deployment; a human-readable
    # console renderer for local dev (nicer to read while hacking).
    is_dev = os.environ.get("ENVIRONMENT", "development").strip().lower() not in (
        "production",
        "prod",
        "staging",
    )

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _request_context_processor,
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    renderer = (
        structlog.dev.ConsoleRenderer(
            colors=True, exception_formatter=structlog.dev.plain_traceback
        )
        if is_dev
        else structlog.processors.JSONRenderer()
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        # Plain stdlib records (not from structlog) get the same correlation fields.
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handlers: list[logging.Handler] = [handler]

    log_file = os.environ.get("APP_LOG_FILE", "").strip()
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=20 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.processors.JSONRenderer(),
                ],
                foreign_pre_chain=shared_processors,
            )
        )
        handlers.append(file_handler)

    root = logging.getLogger()
    root.handlers = handlers
    root.setLevel(level)


def get_logger(name: str = "app"):
    return structlog.get_logger(name)


#: Dedicated logger for the one-line-per-request access log (middleware).
access_logger = structlog.get_logger("app.access")

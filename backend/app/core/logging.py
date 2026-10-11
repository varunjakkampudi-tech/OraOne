"""Structured logging configuration (structlog).

One JSON log line per request, with a stable schema every log aggregator
(Loki, CloudWatch, Datadog, whatever) can parse without custom parsing
rules: timestamp, level, event, request_id, method, path, status_code,
duration_ms, user_id, organization_id. Replaces the hand-rolled
``json.dumps(...)`` access logger that used to live inline in server.py.

``configure_logging()`` is idempotent — safe to call multiple times (e.g.
once from server.py, once from a test fixture) without duplicating handlers.
"""
from __future__ import annotations

import logging
import os
import sys

import structlog

_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    # JSON in anything that looks like a real deployment; a human-readable
    # console renderer for local dev (nicer to read while hacking).
    is_dev = os.environ.get("ENVIRONMENT", "development").strip().lower() not in (
        "production", "prod", "staging",
    )

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
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
        structlog.dev.ConsoleRenderer(colors=True)
        if is_dev
        else structlog.processors.JSONRenderer()
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def get_logger(name: str = "app"):
    return structlog.get_logger(name)


#: Dedicated logger for the one-line-per-request access log (server.py).
access_logger = structlog.get_logger("app.access")

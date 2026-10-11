"""OpenTelemetry tracing — off by default, on when configured.

Matches the rest of the codebase's graceful-degradation posture (Redis,
S3, email, billing all work with zero config and upgrade automatically
once real credentials/endpoints show up): if ``OTEL_EXPORTER_OTLP_ENDPOINT``
is unset, tracing is a complete no-op (the ``opentelemetry-api`` calls
FastAPI's auto-instrumentation makes are harmless no-ops without a
configured SDK) — no collector, no Jaeger, nothing required to run the
app locally. Set the endpoint (e.g. an OTel Collector, Jaeger, Honeycomb,
Grafana Tempo) to start exporting real traces.

``request_id`` (already stamped on every request by server.py's
``request_context_mw``) is attached to the active span as an attribute so
a trace and a structured log line for the same request can be correlated
by that id even without a full OTLP pipeline.
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger("app.tracing")

_configured = False


def configure_tracing(app=None) -> bool:
    """Best-effort OpenTelemetry setup. Returns True if tracing is active.

    Safe to call even when the ``opentelemetry-*`` packages aren't
    installed or no endpoint is configured — logs once and no-ops.
    """
    global _configured
    if _configured:
        return True

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    service_name = os.environ.get("OTEL_SERVICE_NAME", "oraone-api")

    if not endpoint:
        log.info("tracing: OTEL_EXPORTER_OTLP_ENDPOINT unset — tracing disabled")
        _configured = True
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as e:
        log.warning("tracing: opentelemetry packages not installed (%s); tracing disabled", e)
        _configured = True
        return False

    try:
        resource = Resource.create({SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
        trace.set_tracer_provider(provider)

        if app is not None:
            FastAPIInstrumentor.instrument_app(app)

        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument()
        except Exception:  # noqa: BLE001 — optional instrumentation
            pass

        log.info("tracing: OpenTelemetry active, exporting to %s (service=%s)", endpoint, service_name)
        _configured = True
        return True
    except Exception as e:  # noqa: BLE001 — never let tracing setup crash the app
        log.warning("tracing: setup failed (%s); tracing disabled", e)
        _configured = True
        return False


def current_trace_id() -> str | None:
    """The active span's trace id (hex), or None if tracing is inactive."""
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        ctx = span.get_span_context()
        if not ctx or not ctx.is_valid:
            return None
        return format(ctx.trace_id, "032x")
    except Exception:  # noqa: BLE001
        return None

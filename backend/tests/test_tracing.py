"""OpenTelemetry tracing config — must be a true no-op when unconfigured,
and must not crash even when a (fake/unreachable) OTLP endpoint is set."""
from __future__ import annotations

import importlib


def _reload_tracing_module():
    """`configure_tracing` caches `_configured` at module level; reload for
    a clean slate between test cases."""
    from app.core import tracing as tracing_module

    return importlib.reload(tracing_module)


def test_tracing_disabled_by_default(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    tracing = _reload_tracing_module()
    assert tracing.configure_tracing() is False
    assert tracing.current_trace_id() is None


def test_tracing_setup_does_not_crash_with_unreachable_endpoint(monkeypatch):
    # Doesn't need to actually reach anything — BatchSpanProcessor exports
    # asynchronously in the background and swallows connection errors.
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:1")
    tracing = _reload_tracing_module()
    result = tracing.configure_tracing()
    # True if opentelemetry packages are installed and setup succeeded,
    # False if they aren't — either way, must not raise.
    assert result in (True, False)

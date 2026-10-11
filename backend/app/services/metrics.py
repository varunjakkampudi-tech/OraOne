"""Metrics registry with a pluggable backend.

OraOne doesn't ship a Prometheus client dependency, so the default backend is a
small, thread-safe **in-process** registry supporting the two shapes we need:

    * **Counters** — monotonically increasing tallies, optionally labelled
      (e.g. ``authorization_total{outcome="deny"}``).
    * **Histograms** — latency distributions summarised as count / sum / a few
      fixed buckets (enough for p50/p95-style dashboards without a TSDB).

Call sites only ever use the module-level facade — :func:`inc` / :func:`observe`
/ :func:`snapshot` / :func:`prometheus_text` — which delegate to the active
:class:`MetricsBackend`. That indirection is the seam for shipping metrics to a
real system later:

    :class:`InProcessBackend`     — default; single process, single lock.
    :class:`PrometheusBackend`    — DESIGN STUB; maps to ``prometheus_client``.
    :class:`OpenTelemetryBackend` — DESIGN STUB; maps to OTel meters.

Select via ``METRICS_BACKEND`` (``inprocess`` | ``prometheus`` | ``otel``). The
stub backends lazily import their (absent) dependency and the factory falls
back to in-process if it isn't installed, so nothing breaks by default.
"""
from __future__ import annotations

import logging
import os
import threading
from abc import ABC, abstractmethod
from typing import Any

log = logging.getLogger("app.metrics")

# Upper bounds (ms) for latency histograms. "+Inf" is implied by ``count``.
_DEFAULT_BUCKETS_MS = (1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500)


def _label_signature(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    return ",".join(f"{k}={labels[k]}" for k in sorted(labels))


def _decode_labels(sig: str) -> dict[str, str]:
    if not sig:
        return {}
    out: dict[str, str] = {}
    for pair in sig.split(","):
        k, _, v = pair.partition("=")
        out[k] = v
    return out


# --------------------------------------------------------------------------- #
# Backend interface                                                           #
# --------------------------------------------------------------------------- #
class MetricsBackend(ABC):
    """Where metrics are recorded. Swap without touching call sites."""

    name: str = "backend"

    @abstractmethod
    def inc(self, name: str, amount: float = 1.0, **labels: str) -> None:
        ...

    @abstractmethod
    def observe(self, name: str, value: float, buckets: tuple[int, ...] = _DEFAULT_BUCKETS_MS) -> None:
        ...

    def snapshot(self) -> dict[str, Any]:
        """JSON-friendly view (in-process only; remote backends may be empty)."""
        return {"counters": {}, "histograms": {}, "backend": self.name}

    def prometheus_text(self) -> str:
        return ""

    def reset(self) -> None:
        ...


class InProcessBackend(MetricsBackend):
    """Thread-safe in-memory counters + histograms (single process)."""

    name = "inprocess"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # name -> { label_signature: count }.  The empty-label series uses key "".
        self._counters: dict[str, dict[str, float]] = {}
        # name -> { "count": n, "sum": s, "buckets": {le: n} }
        self._histograms: dict[str, dict[str, Any]] = {}

    def inc(self, name: str, amount: float = 1.0, **labels: str) -> None:
        sig = _label_signature({k: str(v) for k, v in labels.items()})
        with self._lock:
            series = self._counters.setdefault(name, {})
            series[sig] = series.get(sig, 0.0) + amount

    def observe(self, name: str, value: float, buckets: tuple[int, ...] = _DEFAULT_BUCKETS_MS) -> None:
        with self._lock:
            h = self._histograms.get(name)
            if h is None:
                h = {"count": 0, "sum": 0.0, "buckets": {b: 0 for b in buckets}}
                self._histograms[name] = h
            h["count"] += 1
            h["sum"] += value
            for b in h["buckets"]:
                if value <= b:
                    h["buckets"][b] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters: dict[str, Any] = {}
            for name, series in self._counters.items():
                if list(series.keys()) == [""]:
                    counters[name] = series[""]
                else:
                    counters[name] = [
                        {"labels": _decode_labels(sig), "value": val}
                        for sig, val in series.items()
                    ]
            histograms: dict[str, Any] = {}
            for name, h in self._histograms.items():
                count = h["count"]
                total = h["sum"]
                histograms[name] = {
                    "count": count,
                    "sum": round(total, 3),
                    "avg": round(total / count, 3) if count else 0.0,
                    "buckets": {str(b): n for b, n in h["buckets"].items()},
                }
        return {"counters": counters, "histograms": histograms, "backend": self.name}

    def prometheus_text(self) -> str:
        lines: list[str] = []
        with self._lock:
            for name, series in self._counters.items():
                lines.append(f"# TYPE {name} counter")
                for sig, val in series.items():
                    labels = _decode_labels(sig)
                    label_str = (
                        "{" + ",".join(f'{k}="{v}"' for k, v in labels.items()) + "}"
                        if labels else ""
                    )
                    lines.append(f"{name}{label_str} {val}")
            for name, h in self._histograms.items():
                lines.append(f"# TYPE {name} histogram")
                for b in sorted(h["buckets"]):
                    lines.append(f'{name}_bucket{{le="{b}"}} {h["buckets"][b]}')
                lines.append(f'{name}_bucket{{le="+Inf"}} {h["count"]}')
                lines.append(f"{name}_count {h['count']}")
                lines.append(f"{name}_sum {h['sum']}")
        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._histograms.clear()


class PrometheusBackend(MetricsBackend):
    """DESIGN STUB — record into ``prometheus_client`` collectors.

    Not wired by default (the dependency isn't installed). It lazily creates
    Counters/Histograms on first use; ``prometheus_text`` renders via
    ``generate_latest``. Construction raises if the package is missing so the
    factory can fall back to in-process.
    """

    name = "prometheus"

    def __init__(self) -> None:
        try:
            import prometheus_client  # type: ignore
        except Exception as e:  # pragma: no cover — optional dependency
            raise RuntimeError(
                "PrometheusBackend requires the 'prometheus_client' package."
            ) from e
        self._client = prometheus_client
        self._lock = threading.Lock()
        self._counters: dict[str, Any] = {}
        self._histograms: dict[str, Any] = {}

    def _counter(self, name: str, labelnames: tuple[str, ...]):  # pragma: no cover
        with self._lock:
            c = self._counters.get(name)
            if c is None:
                c = self._client.Counter(name, name, labelnames)
                self._counters[name] = c
            return c

    def inc(self, name: str, amount: float = 1.0, **labels: str) -> None:  # pragma: no cover
        c = self._counter(name, tuple(sorted(labels)))
        (c.labels(**labels) if labels else c).inc(amount)

    def observe(self, name: str, value: float, buckets: tuple[int, ...] = _DEFAULT_BUCKETS_MS) -> None:  # pragma: no cover
        with self._lock:
            h = self._histograms.get(name)
            if h is None:
                h = self._client.Histogram(name, name, buckets=buckets)
                self._histograms[name] = h
        h.observe(value)

    def prometheus_text(self) -> str:  # pragma: no cover
        return self._client.generate_latest().decode("utf-8")


class OpenTelemetryBackend(MetricsBackend):
    """DESIGN STUB — record into OpenTelemetry meters.

    Not wired by default. Lazily obtains a meter and maps counters/histograms
    to OTel instruments; export is handled by the configured OTel pipeline
    (OTLP → Collector → Prometheus/CloudWatch). Construction raises if the SDK
    is missing so the factory can fall back to in-process.
    """

    name = "otel"

    def __init__(self) -> None:
        try:
            from opentelemetry import metrics as otel_metrics  # type: ignore
        except Exception as e:  # pragma: no cover — optional dependency
            raise RuntimeError(
                "OpenTelemetryBackend requires the 'opentelemetry-api' package."
            ) from e
        self._meter = otel_metrics.get_meter("oraone.authorization")
        self._lock = threading.Lock()
        self._counters: dict[str, Any] = {}
        self._histograms: dict[str, Any] = {}

    def inc(self, name: str, amount: float = 1.0, **labels: str) -> None:  # pragma: no cover
        with self._lock:
            c = self._counters.get(name)
            if c is None:
                c = self._meter.create_counter(name)
                self._counters[name] = c
        c.add(amount, attributes=labels or None)

    def observe(self, name: str, value: float, buckets: tuple[int, ...] = _DEFAULT_BUCKETS_MS) -> None:  # pragma: no cover
        with self._lock:
            h = self._histograms.get(name)
            if h is None:
                h = self._meter.create_histogram(name)
                self._histograms[name] = h
        h.record(value)


# --------------------------------------------------------------------------- #
# Active backend + module-level facade                                        #
# --------------------------------------------------------------------------- #
def _make_backend() -> MetricsBackend:
    choice = os.getenv("METRICS_BACKEND", "inprocess").strip().lower()
    if choice in {"prometheus", "prom"}:
        try:
            b = PrometheusBackend()
            log.info("metrics backend: prometheus")
            return b
        except Exception as e:  # pragma: no cover
            log.warning("prometheus metrics backend unavailable (%s); using in-process.", e)
    elif choice in {"otel", "opentelemetry"}:
        try:
            b = OpenTelemetryBackend()
            log.info("metrics backend: opentelemetry")
            return b
        except Exception as e:  # pragma: no cover
            log.warning("otel metrics backend unavailable (%s); using in-process.", e)
    return InProcessBackend()


_backend: MetricsBackend = _make_backend()


def use_backend(backend: MetricsBackend) -> None:
    """Swap the active metrics backend (tests / runtime configuration)."""
    global _backend
    _backend = backend


def get_backend() -> MetricsBackend:
    return _backend


def inc(name: str, amount: float = 1.0, **labels: str) -> None:
    """Increment a counter series by ``amount`` (default 1)."""
    _backend.inc(name, amount, **labels)


def observe(name: str, value: float, buckets: tuple[int, ...] = _DEFAULT_BUCKETS_MS) -> None:
    """Record one observation (e.g. a latency in ms) into a histogram."""
    _backend.observe(name, value, buckets)


def snapshot() -> dict[str, Any]:
    """Return a JSON-serialisable view of every metric."""
    return _backend.snapshot()


def prometheus_text() -> str:
    """Render the registry in Prometheus text-exposition format."""
    return _backend.prometheus_text()


def reset() -> None:
    """Clear all metrics (used by tests)."""
    _backend.reset()

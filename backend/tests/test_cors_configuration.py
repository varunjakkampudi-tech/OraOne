"""Regression: unconfigured dashboard CORS never grants arbitrary origins."""

import pytest

from app.core.cors import dashboard_origins


def test_development_default_is_exact_loopback_origins(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert "http://localhost:3001" in dashboard_origins()
    assert "*" not in dashboard_origins()
    assert "https://unauthorized.example" not in dashboard_origins()


@pytest.mark.parametrize("environment", ["production", "prod", "staging"])
def test_deployment_requires_explicit_origins(monkeypatch, environment):
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    with pytest.raises(RuntimeError):
        dashboard_origins()


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://oraone.in,*",
        "https://good.example/path",
        "https://user:password@good.example",
        "https://good.example?query=1",
    ],
)
def test_unsafe_origin_configuration_is_rejected(monkeypatch, origin):
    monkeypatch.setenv("CORS_ORIGINS", origin)
    with pytest.raises(RuntimeError):
        dashboard_origins()


def test_exact_origins_are_normalized_and_deduplicated(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://oraone.in/, https://oraone.in")
    assert dashboard_origins() == ["https://oraone.in"]

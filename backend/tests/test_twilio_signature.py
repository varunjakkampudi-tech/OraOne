"""Twilio webhook signatures: the inbound route must reject anything not signed by Twilio."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.omnichannel import routes as omni_routes
from app.services.channels import adapters

AUTH_TOKEN = "12345"
PUBLIC_BASE = "https://api.example.test"

# Known-answer vector: the URL and fields from Twilio's webhook-security docs, signed with a
# test token of "12345" using the documented algorithm (HMAC-SHA1 over URL + sorted fields).
# The docs' own sample signature was made with an undisclosed token, so it is not used here.
DOC_URL = "https://mycompany.com/myapp"
DOC_PARAMS = {
    "CallSid": "CA1234567890ABCDE",
    "Caller": "+12349013030",
    "Digits": "1234",
    "From": "+12349013030",
    "To": "+18005551212",
}
DOC_SIGNATURE = "3KI2uRuYyAdhZIJXcpU0izDUzWI="


def test_matches_twilio_documented_example():
    assert adapters.verify_twilio_signature(
        AUTH_TOKEN, DOC_URL, DOC_PARAMS, DOC_SIGNATURE
    )


def test_rejects_altered_field():
    tampered = {**DOC_PARAMS, "Body": "injected"}
    assert not adapters.verify_twilio_signature(
        AUTH_TOKEN, DOC_URL, tampered, DOC_SIGNATURE
    )


def test_rejects_wrong_token_and_missing_inputs():
    assert not adapters.verify_twilio_signature(
        "other", DOC_URL, DOC_PARAMS, DOC_SIGNATURE
    )
    assert not adapters.verify_twilio_signature(AUTH_TOKEN, DOC_URL, DOC_PARAMS, None)
    assert not adapters.verify_twilio_signature("", DOC_URL, DOC_PARAMS, DOC_SIGNATURE)


@pytest.fixture
def client(monkeypatch):
    cfg = SimpleNamespace(twilio_auth_token=AUTH_TOKEN, public_api_base_url=PUBLIC_BASE)
    monkeypatch.setattr(omni_routes, "get_channels_config", lambda: cfg)
    monkeypatch.setattr(adapters, "get_channels_config", lambda: cfg)
    app = FastAPI()
    app.include_router(omni_routes.router)
    return TestClient(app)


def test_unsigned_twilio_webhook_is_rejected(client):
    response = client.post(
        "/api/channels/twilio/inbound",
        data={
            "From": "whatsapp:+447700900123",
            "To": "whatsapp:+15550000000",
            "Body": "hi",
        },
    )
    assert response.status_code == 401


def test_wrong_signature_is_rejected(client):
    response = client.post(
        "/api/channels/twilio/inbound",
        data={
            "From": "whatsapp:+447700900123",
            "To": "whatsapp:+15550000000",
            "Body": "hi",
        },
        headers={"X-Twilio-Signature": "bad"},
    )
    assert response.status_code == 401


def test_missing_public_url_fails_closed(monkeypatch):
    cfg = SimpleNamespace(twilio_auth_token=AUTH_TOKEN, public_api_base_url="")
    monkeypatch.setattr(omni_routes, "get_channels_config", lambda: cfg)
    app = FastAPI()
    app.include_router(omni_routes.router)
    response = TestClient(app).post(
        "/api/channels/twilio/inbound",
        data={"From": "x", "To": "y", "Body": "hi"},
        headers={"X-Twilio-Signature": DOC_SIGNATURE},
    )
    assert response.status_code == 401

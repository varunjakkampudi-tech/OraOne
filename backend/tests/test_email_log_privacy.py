"""Verification secrets must not appear in delivery diagnostics."""

import logging

from app.services import email_service


def test_disabled_delivery_does_not_log_otp_subject(monkeypatch, caplog):
    monkeypatch.setattr(
        email_service, "render", lambda *args, **kwargs: "<p>654321</p>"
    )
    monkeypatch.setattr(email_service, "_smtp_config", lambda: None)
    with caplog.at_level(logging.INFO, logger="app.email"):
        assert (
            email_service.send_email(
                to="test@example.com",
                subject="654321 is your sign-in code",
                template="login_otp",
                context={"code": "654321"},
            )
            is False
        )
    assert "654321" not in caplog.text
    assert "login_otp" in caplog.text

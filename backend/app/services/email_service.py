"""Transactional email service.

Renders the branded HTML templates under ``app/emails/templates`` and sends
them over SMTP. Delivery is best-effort: when ``SMTP_HOST`` is not configured
the rendered email is logged as not sent and the call returns ``False``, so
callers never crash because mail is not configured.

The renderer is dependency-free. Templates use ``{{ name }}`` placeholders whose
values are HTML-escaped. A single ``__CONTENT__`` marker in ``_base.html`` is
where each body template is injected.
"""

from __future__ import annotations

import hashlib
import html
import logging
import os
import re
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.core.log_redaction import redact_email
from app.services import resend_client

log = logging.getLogger("app.email")

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "emails" / "templates"
_TOKEN_RE = re.compile(r"{{\s*(\w+)\s*}}")


def _app_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def _smtp_config() -> dict | None:
    host = os.environ.get("SMTP_HOST")
    if not host:
        return None
    return {
        "host": host,
        "port": int(os.environ.get("SMTP_PORT", "465")),
        "user": os.environ.get("SMTP_USER"),
        "password": os.environ.get("SMTP_PASSWORD"),
        "from": os.environ.get("SMTP_FROM") or os.environ.get("SMTP_USER"),
        "use_ssl": os.environ.get("SMTP_USE_SSL", "true").lower() != "false",
    }


def delivery_configured() -> bool:
    """True when SMTP settings are present, so mail can actually leave the server."""
    return _smtp_config() is not None


def _send_via_smtp(*, to: str, subject: str, html_body: str, cfg: dict) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["from"]
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if cfg["use_ssl"]:
        server = smtplib.SMTP_SSL(
            cfg["host"], cfg["port"], context=ssl.create_default_context(), timeout=15
        )
    else:
        server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=15)
    try:
        if not cfg["use_ssl"]:
            server.starttls(context=ssl.create_default_context())
        if cfg["user"] and cfg["password"]:
            server.login(cfg["user"], cfg["password"])
        server.sendmail(cfg["from"], [to], msg.as_string())
    finally:
        server.quit()
    return True


@lru_cache(maxsize=32)
def _load(name: str) -> str:
    path = _TEMPLATE_DIR / name
    return path.read_text(encoding="utf-8")


def _substitute(template: str, context: dict) -> str:
    """Replace ``{{ key }}`` tokens with HTML-escaped values from ``context``."""

    def repl(match: re.Match) -> str:
        key = match.group(1)
        value = context.get(key, "")
        return html.escape(str(value), quote=True)

    return _TOKEN_RE.sub(repl, template)


def render(
    template_name: str, subject: str, context: dict, *, preheader: str = ""
) -> str:
    """Render a body template inside the shared base layout. Returns full HTML."""
    base_ctx = {
        "subject": subject,
        "preheader": preheader or subject,
        "year": datetime.now(timezone.utc).year,
        "app_url": _app_url(),
        **context,
    }
    body = _substitute(_load(template_name), base_ctx)
    shell = _substitute(_load("_base.html"), base_ctx)
    return shell.replace("__CONTENT__", body)


def send_email(
    *,
    to: str,
    subject: str,
    template: str,
    context: dict,
    preheader: str = "",
) -> bool:
    """Render and send an email. Returns True if handed off to a provider, else False.

    Never raises on delivery failure — logs and returns False so callers can
    fire-and-forget notifications without guarding every call site.
    """
    html_body = render(template, subject, context, preheader=preheader)

    smtp_cfg = _smtp_config()
    if smtp_cfg:
        try:
            _send_via_smtp(to=to, subject=subject, html_body=html_body, cfg=smtp_cfg)
            log.info(
                "email sent via SMTP (%s) → to=%s template=%r",
                smtp_cfg["host"],
                redact_email(to),
                template,
            )
            return True
        except Exception as exc:  # pragma: no cover - network/credential dependent
            log.warning(
                "SMTP send failed → to=%s template=%r error_type=%s",
                redact_email(to),
                template,
                type(exc).__name__,
            )

    log.info(
        "email (SMTP_HOST not configured) → to=%s template=%r [not sent]",
        redact_email(to),
        template,
    )
    return False


# ── typed convenience wrappers (one per template) ──────────────────────────


#: Sign-in codes expire after this long. Keep in step with ``auth_service``.
LOGIN_OTP_EXPIRES_IN = "5 minutes"


def _login_otp_text(code: str, expires_in: str) -> str:
    """Plain-text part of the sign-in email (clients that do not render HTML)."""
    return (
        f"Your OraOne sign-in code is {code}.\n\n"
        f"It expires in {expires_in} and works once. Do not share it with anyone.\n\n"
        "If you did not ask to sign in, you can ignore this email. "
        "No one can sign in without this code.\n"
    )


def send_login_otp(
    to: str, *, code: str, expires_in: str = LOGIN_OTP_EXPIRES_IN
) -> bool:
    """Email a sign-in code. Uses Resend when ``RESEND_API_KEY`` is set, else SMTP.

    Returns True only when the provider accepted the message. The caller treats
    False as "no code was delivered".
    """
    subject = f"{code} is your OraOne sign-in code"
    preheader = "Enter this code to finish signing in."
    context = {"code": code, "expires_in": expires_in}
    api_key = settings.resend_api_key
    if api_key:
        html_body = render("login_otp.html", subject, context, preheader=preheader)
        # Same recipient and code always map to the same key, so a retried request
        # cannot send a second copy of an identical code.
        idempotency_key = hashlib.sha256(f"login-otp|{to}|{code}".encode()).hexdigest()
        return resend_client.send(
            api_key=api_key,
            from_address=settings.resend_from,
            to=to,
            subject=subject,
            html=html_body,
            text=_login_otp_text(code, expires_in),
            idempotency_key=idempotency_key,
        )
    if settings.is_production:
        # Production sign-in codes go through Resend only. Falling back to SMTP here
        # would send codes through a second, unaudited provider, so refuse instead.
        log.error("login_otp_not_sent reason=resend_not_configured")
        return False
    return send_email(
        to=to,
        subject=subject,
        template="login_otp.html",
        preheader=preheader,
        context=context,
    )


def send_team_invite(
    to: str,
    *,
    org_name: str,
    inviter_name: str,
    role: str,
    accept_url: str,
    expires_in: str = "7 days",
) -> bool:
    return send_email(
        to=to,
        subject=f"You're invited to join {org_name} on OraOne",
        template="team_invite.html",
        preheader=f"{inviter_name} invited you as {role}.",
        context={
            "org_name": org_name,
            "inviter_name": inviter_name,
            "role": role,
            "cta_url": accept_url,
            "expires_in": expires_in,
        },
    )

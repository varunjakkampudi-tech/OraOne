"""Transactional email service.

Renders the branded HTML templates under ``app/emails/templates`` and sends
them. Delivery is **best-effort and degrades gracefully**, mirroring the rest of
the codebase, and tries providers in this order:

1. If ``SMTP_HOST`` is set, send over real SMTP (e.g. a Hostinger/Gmail/any
   mailbox). This has no "sandbox" recipient restriction, unlike a fresh SES
   account, so it's the most reliable path for a brand-new AWS account still
   awaiting SES production access.
2. Else if ``EMAIL_FROM`` is set and ``boto3`` can create an SES client, the
   email is sent through Amazon SES.
3. Otherwise the rendered email is logged at INFO level (development mode) and
   the call still succeeds, so callers never crash because email isn't
   configured.

The renderer is dependency-free. Templates use ``{{ name }}`` placeholders whose
values are HTML-escaped. A single ``__CONTENT__`` marker in ``_base.html`` is
where each body template is injected.
"""
from __future__ import annotations

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

log = logging.getLogger("app.email")

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "emails" / "templates"
_TOKEN_RE = re.compile(r"{{\s*(\w+)\s*}}")


def _app_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def _from_address() -> str | None:
    return (
        os.environ.get("SMTP_FROM")
        or os.environ.get("EMAIL_FROM")
        or os.environ.get("SES_FROM_EMAIL")
        or None
    )


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


def _send_via_smtp(*, to: str, subject: str, html_body: str, cfg: dict) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["from"]
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if cfg["use_ssl"]:
        server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ssl.create_default_context(), timeout=15)
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


def render(template_name: str, subject: str, context: dict, *, preheader: str = "") -> str:
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
            log.info("email sent via SMTP (%s) → to=%s subject=%r", smtp_cfg["host"], to, subject)
            return True
        except Exception as exc:  # pragma: no cover - network/credential dependent
            log.warning("SMTP send failed → to=%s subject=%r err=%s", to, subject, exc)
            # fall through to SES below, if configured

    sender = _from_address()
    if not sender:
        log.info("email (no SMTP_HOST/EMAIL_FROM configured) → to=%s subject=%r [not sent]", to, subject)
        return False

    try:
        import boto3

        region = os.environ.get("SES_REGION") or os.environ.get("AWS_REGION", "us-east-1")
        client = boto3.client("ses", region_name=region)
        client.send_email(
            Source=sender,
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )
        log.info("email sent via SES → to=%s subject=%r", to, subject)
        return True
    except Exception as exc:  # pragma: no cover - network/credential dependent
        log.warning("email send failed → to=%s subject=%r err=%s", to, subject, exc)
        return False


# ── typed convenience wrappers (one per template) ──────────────────────────

def send_welcome(to: str, *, first_name: str, org_name: str) -> bool:
    return send_email(
        to=to,
        subject="Welcome to OraOne",
        template="welcome.html",
        preheader="Your workspace is ready — here's how to go live.",
        context={
            "first_name": first_name,
            "org_name": org_name,
            "cta_url": f"{_app_url()}/app/getting-started",
        },
    )


def send_verify_email(to: str, *, verify_url: str, code: str, expires_in: str = "24 hours") -> bool:
    return send_email(
        to=to,
        subject="Verify your email",
        template="verify_email.html",
        preheader="Confirm your email to activate your OraOne account.",
        context={"cta_url": verify_url, "code": code, "expires_in": expires_in},
    )


def send_password_reset(to: str, *, reset_url: str, code: str, expires_in: str = "1 hour") -> bool:
    return send_email(
        to=to,
        subject="Reset your OraOne password",
        template="password_reset.html",
        preheader="Use this link to set a new password.",
        context={"email": to, "cta_url": reset_url, "code": code, "expires_in": expires_in},
    )


def send_login_otp(to: str, *, code: str, expires_in: str = "10 minutes") -> bool:
    return send_email(
        to=to,
        subject=f"{code} is your OraOne sign-in code",
        template="login_otp.html",
        preheader="Enter this code to finish signing in.",
        context={"code": code, "expires_in": expires_in},
    )


def send_team_invite(
    to: str, *, org_name: str, inviter_name: str, role: str, accept_url: str, expires_in: str = "7 days"
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


def send_lead_captured(
    to: str, *, agent_name: str, channel: str, lead_name: str, lead_phone: str,
    lead_email: str, lead_intent: str, lead_url: str,
) -> bool:
    return send_email(
        to=to,
        subject=f"New lead captured by {agent_name}",
        template="lead_captured.html",
        preheader=f"{lead_name} from {channel}.",
        context={
            "agent_name": agent_name, "channel": channel, "lead_name": lead_name,
            "lead_phone": lead_phone, "lead_email": lead_email,
            "lead_intent": lead_intent, "cta_url": lead_url,
        },
    )


def send_conversation_escalated(
    to: str, *, agent_name: str, channel: str, customer_name: str, reason: str,
    last_message: str, escalated_at: str, conversation_url: str,
) -> bool:
    return send_email(
        to=to,
        subject="A conversation needs a human",
        template="conversation_escalated.html",
        preheader=f"{agent_name} escalated a {channel} conversation.",
        context={
            "agent_name": agent_name, "channel": channel, "customer_name": customer_name,
            "reason": reason, "last_message": last_message, "escalated_at": escalated_at,
            "cta_url": conversation_url,
        },
    )


def send_usage_warning(
    to: str, *, org_name: str, plan_name: str, metric_label: str,
    used: str, limit: str, percent: int, plans_url: str,
) -> bool:
    return send_email(
        to=to,
        subject=f"You're approaching your {metric_label} limit",
        template="usage_warning.html",
        preheader=f"{percent}% of your {metric_label} used.",
        context={
            "org_name": org_name, "plan_name": plan_name, "metric_label": metric_label,
            "used": used, "limit": limit, "percent": percent, "cta_url": plans_url,
        },
    )


def send_subscription_receipt(
    to: str, *, first_name: str, plan_name: str, billing_cycle: str, amount: str,
    renewal_date: str, invoice_number: str, payment_method: str, billing_url: str,
) -> bool:
    return send_email(
        to=to,
        subject=f"Your {plan_name} subscription is active",
        template="subscription_receipt.html",
        preheader=f"Receipt for {plan_name}.",
        context={
            "first_name": first_name, "plan_name": plan_name, "billing_cycle": billing_cycle,
            "amount": amount, "renewal_date": renewal_date, "invoice_number": invoice_number,
            "payment_method": payment_method, "cta_url": billing_url,
        },
    )


def send_weekly_digest(
    to: str, *, org_name: str, period_start: str, period_end: str,
    conversations: str, leads: str, resolution_rate: str, csat: str, analytics_url: str,
) -> bool:
    return send_email(
        to=to,
        subject="Your weekly OraOne summary",
        template="weekly_digest.html",
        preheader=f"{conversations} conversations, {leads} leads this week.",
        context={
            "org_name": org_name, "period_start": period_start, "period_end": period_end,
            "conversations": conversations, "leads": leads,
            "resolution_rate": resolution_rate, "csat": csat, "cta_url": analytics_url,
        },
    )

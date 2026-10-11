"""Channels & Deploy service — the customer-facing surface of the Universal Agent.

One agent serves many channels (Website Chat, Widget, WhatsApp, SMS, API,
Webhooks, Forms). This module is the single source of truth for:

* ensuring an :class:`AgentChannel` row exists for every supported channel,
* enabling / disabling / configuring a channel,
* ensuring a backing :class:`Widget` (public_key) for the embeddable channels,
* assembling everything a developer needs to *deploy*: the one-line embed,
  the npm package, the JS SDK, and copy-paste install guides for every major
  web platform,
* managing the domain allow-list, and
* verifying a live installation from widget telemetry.

Nothing here duplicates AI logic — answers still flow through the existing
AgentRuntime / RAG / widget pipeline. This only wires the agent to its
delivery surfaces.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.database.models.agent import Agent
from app.database.models.agent_channel import AgentChannel, ChannelStatus
from app.database.models.widget import Widget, WidgetStatus, WidgetType
from app.database.models.widget_domain import WidgetDomain
from app.database.models.widget_event import WidgetEvent
from app.services import widget_service


# ── Supported channels for the Universal Agent (ordered for the UI) ──
# ``channel`` is stored verbatim in agent_channels.channel (String(20)).
CHANNEL_DEFS: list[dict[str, Any]] = [
    {
        "channel": "chat",
        "label": "Website Chat",
        "description": "In-page conversational chat backed by this agent.",
        "icon": "messages",
        "default_enabled": True,
        "embeddable": True,
    },
    {
        "channel": "widget",
        "label": "Website Widget",
        "description": "Floating chat bubble you drop on any site with one line.",
        "icon": "bubble",
        "default_enabled": True,
        "embeddable": True,
    },
    {
        "channel": "api",
        "label": "API",
        "description": "Call the agent programmatically from your backend.",
        "icon": "code",
        "default_enabled": False,
        "embeddable": False,
    },
    {
        "channel": "webhooks",
        "label": "Webhooks",
        "description": "Push conversation & lead events to your systems.",
        "icon": "webhook",
        "default_enabled": False,
        "embeddable": False,
    },
]

_CHANNEL_BY_KEY = {d["channel"]: d for d in CHANNEL_DEFS}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_valid_channel(channel: str) -> bool:
    return channel in _CHANNEL_BY_KEY


# ─────────────────────────── channels ───────────────────────────

async def ensure_channels(session: AsyncSession, agent: Agent) -> list[AgentChannel]:
    """Find-or-create an AgentChannel row for every supported channel.

    Existing rows (e.g. a channel configured elsewhere) are preserved.
    Uses ``INSERT ... ON CONFLICT DO NOTHING`` for the missing rows so
    concurrent calls for the same agent (e.g. two components mounting at
    once) can't race on the unique ``(agent_id, channel)`` constraint and
    raise an IntegrityError.
    Returns the rows in CHANNEL_DEFS order.
    """
    existing = {
        c.channel: c
        for c in (
            await session.scalars(
                select(AgentChannel).where(AgentChannel.agent_id == agent.id)
            )
        ).all()
    }
    missing = [d for d in CHANNEL_DEFS if d["channel"] not in existing]
    if missing:
        stmt = pg_insert(AgentChannel).values(
            [
                {
                    "organization_id": agent.organization_id,
                    "project_id": agent.project_id,
                    "agent_id": agent.id,
                    "channel": d["channel"],
                    "enabled": bool(d["default_enabled"]),
                    "status": ChannelStatus.active if d["default_enabled"] else ChannelStatus.disabled,
                    "provider": d.get("provider"),
                    "configuration": {},
                }
                for d in missing
            ]
        ).on_conflict_do_nothing(index_elements=["agent_id", "channel"])
        await session.execute(stmt)
        await session.flush()
        existing = {
            c.channel: c
            for c in (
                await session.scalars(
                    select(AgentChannel).where(AgentChannel.agent_id == agent.id)
                )
            ).all()
        }
    return [existing[d["channel"]] for d in CHANNEL_DEFS]


async def _assert_identifier_not_claimed(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    channel: str,
    phone_number: Optional[str] = None,
    bot_token: Optional[str] = None,
    inbound_address: Optional[str] = None,
) -> None:
    """Reject phone/bot-token/inbound-address values another org already owns.

    Inbound webhooks (omnichannel_service._resolve_binding) are unauthenticated
    and route purely by these identifiers, so two organizations configuring
    the same value would let one tenant's messages be delivered to the
    other's agent. Enforcing uniqueness here — the only place these values
    are ever written — closes that gap without touching the webhook path.
    """
    conditions = []
    if phone_number:
        conditions.append(AgentChannel.phone_number == phone_number)
    if bot_token:
        conditions.append(AgentChannel.configuration["bot_token"].astext == bot_token)
    if inbound_address:
        conditions.append(
            AgentChannel.configuration["inbound_address"].astext == inbound_address
        )
    if not conditions:
        return

    for condition in conditions:
        clash = await session.scalar(
            select(AgentChannel.id)
            .where(AgentChannel.channel == channel)
            .where(AgentChannel.organization_id != organization_id)
            .where(condition)
            .limit(1)
        )
        if clash is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "This phone number, bot token, or inbound address is already "
                "in use by another organization.",
            )


async def update_channel(
    session: AsyncSession,
    agent: Agent,
    channel: str,
    *,
    enabled: Optional[bool] = None,
    status: Optional[str] = None,
    phone_number: Optional[str] = None,
    provider: Optional[str] = None,
    configuration: Optional[dict] = None,
) -> AgentChannel:
    rows = await ensure_channels(session, agent)
    row = next((r for r in rows if r.channel == channel), None)
    if row is None:  # pragma: no cover — guarded by caller
        raise ValueError(f"Unknown channel {channel!r}")

    await _assert_identifier_not_claimed(
        session,
        organization_id=agent.organization_id,
        channel=channel,
        phone_number=phone_number or None,
        bot_token=(configuration or {}).get("bot_token"),
        inbound_address=(configuration or {}).get("inbound_address"),
    )

    if enabled is not None:
        row.enabled = bool(enabled)
        # Keep status coherent with the toggle unless the caller overrides it.
        if status is None:
            row.status = ChannelStatus.active if enabled else ChannelStatus.disabled
    if status is not None and status in ChannelStatus.ALL:
        row.status = status
    if phone_number is not None:
        row.phone_number = phone_number or None
    if provider is not None:
        row.provider = provider or None
    if configuration is not None and isinstance(configuration, dict):
        row.configuration = {**(row.configuration or {}), **configuration}

    # Toggling the embeddable channels publishes/pauses the backing widget so
    # the one-line embed goes live the moment "Website Widget" is enabled.
    if channel in ("widget", "chat"):
        widget = await ensure_widget(session, agent)
        if enabled is True and widget.status != WidgetStatus.published:
            widget.status = WidgetStatus.published
            widget.published_at = now_utc()
        elif enabled is False:
            # Only pause if NO embeddable channel remains enabled.
            others = [
                r for r in rows
                if r.channel in ("widget", "chat") and r.channel != channel
            ]
            if not any(o.enabled for o in others):
                widget.status = WidgetStatus.paused
    return row


# ─────────────────────────── widget binding ───────────────────────────

async def ensure_widget(session: AsyncSession, agent: Agent) -> Widget:
    """Find-or-create the Widget that backs this agent's embeddable channels.

    A single widget per agent is enough — it carries the public_key, theme,
    settings and domain allow-list used by every embed surface.
    """
    widget = await session.scalar(
        select(Widget)
        .where(Widget.organization_id == agent.organization_id)
        .where(Widget.agent_id == agent.id)
        .where(Widget.deleted_at.is_(None))
        .order_by(Widget.created_at.asc())
        .limit(1)
    )
    if widget is not None:
        return widget

    cfg = agent.config
    widget = Widget(
        organization_id=agent.organization_id,
        project_id=agent.project_id,
        public_key=_new_key(),
        name=f"{agent.name} Widget",
        status=WidgetStatus.draft,
        widget_type=WidgetType.bubble,
        agent_id=agent.id,
        theme={"primary_color": "#2563EB", "bubble_color": "#2563EB", "mode": "auto"},
        settings={
            "agent_name": agent.name,
            "welcome_message": (cfg.greeting if cfg and cfg.greeting else "Hi! 👋 How can I help you today?"),
        },
    )
    session.add(widget)
    await session.flush()
    return widget


def _new_key() -> str:
    from app.database.models.widget import _gen_public_key

    return _gen_public_key()


# ─────────────────────────── domains ───────────────────────────

async def get_domains(session: AsyncSession, widget: Widget) -> list[str]:
    return await widget_service.widget_domains(session, widget.id)


async def set_domains(
    session: AsyncSession, widget: Widget, domains: list[str]
) -> list[str]:
    """Replace the widget's domain allow-list with the normalised input."""
    wanted: list[str] = []
    seen = set()
    for d in domains or []:
        host = widget_service.normalize_domain(d)
        if host and host not in seen:
            seen.add(host)
            wanted.append(host)

    current = {
        row.domain: row
        for row in (
            await session.scalars(
                select(WidgetDomain).where(WidgetDomain.widget_id == widget.id)
            )
        ).all()
    }
    # Remove dropped, add new.
    for host, row in current.items():
        if host not in seen:
            await session.delete(row)
    for host in wanted:
        if host not in current:
            session.add(WidgetDomain(widget_id=widget.id, domain=host))
    await session.flush()
    return wanted


# ─────────────────────────── verification ───────────────────────────

async def verify_installation(session: AsyncSession, widget: Widget) -> dict:
    """Has the widget ever loaded on a real page? Pull it from telemetry."""
    total = await session.scalar(
        select(func.count(WidgetEvent.id)).where(WidgetEvent.widget_id == widget.id)
    ) or 0
    last_seen = await session.scalar(
        select(func.max(WidgetEvent.created_at)).where(
            WidgetEvent.widget_id == widget.id
        )
    )
    loaded = await session.scalar(
        select(func.count(WidgetEvent.id))
        .where(WidgetEvent.widget_id == widget.id)
        .where(WidgetEvent.event == "loaded")
    ) or 0
    return {
        "installed": bool(loaded),
        "events_count": int(total),
        "loads_count": int(loaded),
        "last_seen": last_seen,
    }


# ─────────────────────────── deploy payload ───────────────────────────

def sdk_methods() -> list[dict[str, str]]:
    return [
        {"name": "OraOne.init(options)", "description": "Optional boot hook — pass { user, context, autoOpen } once the script tag has loaded."},
        {"name": "OraOne.open()", "description": "Open the chat panel."},
        {"name": "OraOne.close()", "description": "Close the chat panel."},
        {"name": "OraOne.startChat(message?)", "description": "Open chat and optionally send a first message."},
        {"name": "OraOne.identifyUser(traits)", "description": "Attach name/email/phone so the agent recognises them everywhere."},
        {"name": "OraOne.updateContext(data)", "description": "Merge live page/user context into the conversation."},
        {"name": "OraOne.trackEvent(name, data)", "description": "Send a custom event (button clicks, page views, …)."},
        {"name": "OraOne.setLeadData(data)", "description": "Push qualified lead fields to your CRM pipeline."},
        {"name": "OraOne.trackPurchase(data)", "description": "Record a purchase / conversion for attribution."},
    ]


def build_snippets(public_key: str) -> dict[str, str]:
    base = widget_service.widget_cdn_base()
    api = widget_service.widget_api_base()
    api_attr = f' data-api="{api}"' if api and api != base else ""

    one_line = (
        f'<script src="{base}/widget.js" '
        f'data-widget-id="{public_key}"{api_attr} async></script>'
    )
    sdk = (
        f'<script src="{base}/widget.js" data-widget-id="{public_key}"{api_attr} async></script>\n'
        "<script>\n"
        "  window.addEventListener('load', function () {\n"
        "    // Tell the agent who this is — recognised across every channel:\n"
        "    OraOne.identifyUser({ name: 'Asha', email: 'asha@acme.com' });\n"
        "  });\n"
        "</script>"
    )
    npm_install = "npm install @oraone/widget"
    npm_import = (
        "import { OraOne } from '@oraone/widget';\n\n"
        f"OraOne.init({{ agentId: '{public_key}' }});"
    )
    return {
        "one_line": one_line,
        "sdk": sdk,
        "npm_install": npm_install,
        "npm_import": npm_import,
    }


def install_guides(public_key: str) -> list[dict[str, str]]:
    base = widget_service.widget_cdn_base()
    api = widget_service.widget_api_base()
    api_attr = f' data-api="{api}"' if api and api != base else ""
    tag = f'<script src="{base}/widget.js" data-widget-id="{public_key}"{api_attr} async></script>'

    react = (
        "// In your root component (e.g. App.jsx)\n"
        "import { useEffect } from 'react';\n\n"
        "export default function OraOneWidget() {\n"
        "  useEffect(() => {\n"
        "    const s = document.createElement('script');\n"
        f"    s.src = '{base}/widget.js';\n"
        f"    s.setAttribute('data-widget-id', '{public_key}');\n"
        + (f"    s.setAttribute('data-api', '{api}');\n" if api_attr else "")
        + "    s.async = true;\n"
        "    document.body.appendChild(s);\n"
        "    return () => { s.remove(); };\n"
        "  }, []);\n"
        "  return null;\n"
        "}"
    )
    nextjs = (
        "// app/layout.tsx (App Router) — add inside <body>\n"
        "import Script from 'next/script';\n\n"
        "<Script\n"
        f"  src=\"{base}/widget.js\"\n"
        f"  data-widget-id=\"{public_key}\"\n"
        + (f"  data-api=\"{api}\"\n" if api_attr else "")
        + "  strategy=\"afterInteractive\"\n"
        "/>"
    )
    vue = (
        "// In your main entry (main.js) or App.vue mounted()\n"
        "const s = document.createElement('script');\n"
        f"s.src = '{base}/widget.js';\n"
        f"s.setAttribute('data-widget-id', '{public_key}');\n"
        + (f"s.setAttribute('data-api', '{api}');\n" if api_attr else "")
        + "s.async = true;\n"
        "document.body.appendChild(s);"
    )
    angular = (
        "// In app.component.ts ngOnInit()\n"
        "ngOnInit(): void {\n"
        "  const s = document.createElement('script');\n"
        f"  s.src = '{base}/widget.js';\n"
        f"  s.setAttribute('data-widget-id', '{public_key}');\n"
        + (f"  s.setAttribute('data-api', '{api}');\n" if api_attr else "")
        + "  s.async = true;\n"
        "  document.body.appendChild(s);\n"
        "}"
    )
    wordpress = (
        "Appearance → Theme File Editor → footer.php, paste before </body>:\n\n"
        f"{tag}\n\n"
        "Or use a plugin like \"Insert Headers and Footers\" and paste the same line."
    )
    shopify = (
        "Online Store → Themes → Edit code → layout/theme.liquid,\n"
        "paste just before </body>:\n\n"
        f"{tag}"
    )
    webflow = (
        "Project Settings → Custom Code → Footer Code, paste:\n\n"
        f"{tag}\n\n"
        "Publish the site to apply."
    )
    html = (
        "Paste this once, just before the closing </body> tag:\n\n"
        f"{tag}"
    )
    return [
        {"platform": "html", "label": "HTML", "language": "html", "code": html},
        {"platform": "react", "label": "React", "language": "jsx", "code": react},
        {"platform": "nextjs", "label": "Next.js", "language": "tsx", "code": nextjs},
        {"platform": "vue", "label": "Vue", "language": "js", "code": vue},
        {"platform": "angular", "label": "Angular", "language": "ts", "code": angular},
        {"platform": "wordpress", "label": "WordPress", "language": "text", "code": wordpress},
        {"platform": "shopify", "label": "Shopify", "language": "text", "code": shopify},
        {"platform": "webflow", "label": "Webflow", "language": "text", "code": webflow},
    ]


def trigger_snippets() -> list[dict[str, str]]:
    return [
        {
            "name": "Button click → open chat",
            "language": "html",
            "code": (
                '<button onclick="OraOne.open()">Chat with us</button>\n\n'
                "<!-- Or start with a pre-filled question: -->\n"
                "<button onclick=\"OraOne.startChat('I need pricing help')\">Talk to sales</button>"
            ),
        },
        {
            "name": "Form submit → identify + follow-up",
            "language": "html",
            "code": (
                "<form id=\"lead-form\">\n"
                "  <input name=\"name\" placeholder=\"Name\" />\n"
                "  <input name=\"email\" type=\"email\" placeholder=\"Email\" />\n"
                "  <button type=\"submit\">Get started</button>\n"
                "</form>\n"
                "<script>\n"
                "  document.getElementById('lead-form').addEventListener('submit', function (e) {\n"
                "    e.preventDefault();\n"
                "    const f = e.target;\n"
                "    OraOne.identifyUser({ name: f.name.value, email: f.email.value });\n"
                "    OraOne.setLeadData({ name: f.name.value, email: f.email.value, source: 'website-form' });\n"
                "    OraOne.startChat('I just signed up — what are my next steps?');\n"
                "  });\n"
                "</script>"
            ),
        },
    ]


async def build_deploy_info(
    session: AsyncSession, agent: Agent
) -> dict:
    widget = await ensure_widget(session, agent)
    channels = await ensure_channels(session, agent)
    domains = await get_domains(session, widget)
    verification = await verify_installation(session, widget)

    embeddable_enabled = any(
        c.enabled for c in channels if c.channel in ("widget", "chat")
    )
    deploy_status = (
        "live"
        if widget.status == WidgetStatus.published and embeddable_enabled
        else ("paused" if widget.status == WidgetStatus.paused else "draft")
    )

    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "public_key": widget.public_key,
        "widget_id": widget.id,
        "widget_status": widget.status,
        "deploy_status": deploy_status,
        "cdn_base": widget_service.widget_cdn_base(),
        "api_base": widget_service.widget_api_base(),
        "snippets": build_snippets(widget.public_key),
        "sdk_methods": sdk_methods(),
        "install_guides": install_guides(widget.public_key),
        "trigger_snippets": trigger_snippets(),
        "domains": domains,
        "verification": verification,
        "theme": widget.theme or {},
        "settings": widget.settings or {},
    }

"""Widget — an embeddable AI chat widget for a customer's website (R6).

A ``Widget`` binds an :class:`Agent` and a :class:`KnowledgeBase` to a
public, white-label chat experience that a business drops onto any site
with a single ``<script>`` tag. The widget is identified publicly by its
``public_key`` (the ``data-widget-id``); the loader fetches a sanitized
config (no secrets) and serves an iframe chat app that answers using the
Enterprise RAG engine (R4).

Statuses / types / positions are plain strings (not DB enums) so the
product surface can evolve without enum migrations.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.widget_domain import WidgetDomain
    from app.database.models.widget_session import WidgetSession


class WidgetStatus:
    draft = "draft"          # created, not published
    published = "published"  # live + embeddable
    paused = "paused"        # temporarily disabled (loader returns 'paused')
    ALL = {draft, published, paused}


class WidgetType:
    bubble = "bubble"        # floating bottom-corner bubble
    inline = "inline"        # embedded inside a page element
    fullpage = "fullpage"    # full-page experience
    popup = "popup"          # auto-opens after a delay
    button = "button"        # opens on a custom button click
    ALL = {bubble, inline, fullpage, popup, button}


class WidgetPosition:
    bottom_right = "bottom-right"
    bottom_left = "bottom-left"
    inline = "inline"
    ALL = {bottom_right, bottom_left, inline}


class WidgetAuthMode:
    public = "public"        # anyone can chat
    identified = "identified"  # host passes signed user context
    sso = "sso"              # enterprise SSO/JWT verified
    ALL = {public, identified, sso}


def _gen_public_key() -> str:
    """Public, non-guessable widget id used as the ``data-widget-id``."""
    return f"wgt_{secrets.token_urlsafe(18)}"


class Widget(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "widgets"
    __table_args__ = (
        Index("ix_widgets_organization_id", "organization_id"),
        Index("ix_widgets_public_key", "public_key", unique=True),
        Index("ix_widgets_status", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # Public embed id (the data-widget-id). Unguessable, rotatable.
    public_key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, default=_gen_public_key
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WidgetStatus.draft, server_default=WidgetStatus.draft
    )
    widget_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WidgetType.bubble, server_default=WidgetType.bubble
    )
    position: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WidgetPosition.bottom_right,
        server_default=WidgetPosition.bottom_right,
    )
    auth_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WidgetAuthMode.public,
        server_default=WidgetAuthMode.public,
    )

    # The AI brain + knowledge source.
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    knowledge_base_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="SET NULL"), nullable=True
    )

    # Branding / colors / typography (no secrets).
    theme: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    # Welcome message, suggested questions, lead capture, behavior toggles.
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    domains: Mapped[list["WidgetDomain"]] = relationship(
        back_populates="widget", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["WidgetSession"]] = relationship(
        back_populates="widget", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Widget {self.name} ({self.status})>"

"""WidgetDomain — an allowed origin for an embedded widget (R6).

The widget loader and chat API enforce a domain allow-list: a widget will
only initialise and answer on origins registered here. An empty allow-list
means the widget is unrestricted (useful in draft/dev), but publishing a
widget for production should always pin its domains.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.widget import Widget


class WidgetDomain(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "widget_domains"
    __table_args__ = (
        UniqueConstraint("widget_id", "domain", name="uq_widget_domains_widget_domain"),
        Index("ix_widget_domains_widget_id", "widget_id"),
    )

    widget_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("widgets.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Normalised host (lowercase, no scheme/port), e.g. "docs.acme.com".
    domain: Mapped[str] = mapped_column(String(255), nullable=False)

    widget: Mapped["Widget"] = relationship(back_populates="domains")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WidgetDomain {self.domain}>"

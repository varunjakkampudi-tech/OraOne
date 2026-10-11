"""Public-facing marketing forms — contact submissions + newsletter signups.

Replaces the legacy MongoDB-backed collections (contact_submissions,
newsletter) now that MongoDB is no longer part of the deployed stack —
see app/api/contact/routes.py.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ContactSubmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "contact_submissions"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="contact", server_default="contact")


class NewsletterSubscriber(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "newsletter_subscribers"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

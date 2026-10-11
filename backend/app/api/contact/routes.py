from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, EmailStr
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.contact import ContactSubmission, NewsletterSubscriber


class ContactIn(BaseModel):
    name: str
    email: EmailStr
    company: Optional[str] = None
    message: str
    type: Optional[str] = "contact"  # contact | demo | sales


class NewsletterIn(BaseModel):
    email: EmailStr


def register_contact_routes(api, get_db) -> None:
    """``get_db`` is the FastAPI dependency callable (app.database.session.get_db)."""
    from fastapi import Depends

    @api.post("/contact")
    async def submit_contact(payload: ContactIn, session: AsyncSession = Depends(get_db)):
        row = ContactSubmission(
            name=payload.name,
            email=payload.email,
            company=payload.company,
            message=payload.message,
            type=payload.type or "contact",
        )
        session.add(row)
        await session.commit()
        return {"message": "Thanks! We'll be in touch shortly.", "id": str(row.id)}

    @api.post("/newsletter")
    async def subscribe_newsletter(payload: NewsletterIn, session: AsyncSession = Depends(get_db)):
        email = payload.email.lower()
        stmt = (
            pg_insert(NewsletterSubscriber)
            .values(email=email)
            .on_conflict_do_update(
                index_elements=["email"],
                set_={"updated_at": datetime.now(timezone.utc)},
            )
        )
        await session.execute(stmt)
        await session.commit()
        return {"message": "Subscribed successfully"}

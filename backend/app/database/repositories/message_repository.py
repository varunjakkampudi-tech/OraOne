"""Message repository."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.database.models.conversation import Conversation
from app.database.models.message import Message
from app.database.repositories.base import BaseRepository
from app.middleware.org_context import OrgContext


class MessageRepository(BaseRepository[Message]):
    model = Message

    async def list_for_conversation(
        self, conversation_id: uuid.UUID, *, limit: int = 500
    ) -> list[Message]:
        q = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list((await self.session.scalars(q)).all())


class OrgScopedMessageRepository(MessageRepository):
    """Tenant-aware Message repo.

    Messages have no direct ``organization_id`` column — they hang off
    Conversation. We therefore JOIN against Conversation on every read
    to guarantee tenant isolation. Writes accept an explicit
    ``conversation_id`` and validate ownership before insert.
    """

    def __init__(self, session, ctx: OrgContext) -> None:
        super().__init__(session)
        self.ctx = ctx
        self.organization_id = ctx.organization_id

    async def _conversation_in_org(self, conversation_id: uuid.UUID) -> bool:
        return bool(
            await self.session.scalar(
                select(Conversation.id)
                .where(Conversation.id == conversation_id)
                .where(Conversation.organization_id == self.organization_id)
                .where(Conversation.deleted_at.is_(None))
            )
        )

    async def list_in_conversation(
        self, conversation_id: uuid.UUID, *, limit: int = 500
    ) -> list[Message]:
        """List messages, but only if the conversation belongs to this org."""
        q = (
            select(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Message.conversation_id == conversation_id)
            .where(Conversation.organization_id == self.organization_id)
            .where(Conversation.deleted_at.is_(None))
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list((await self.session.scalars(q)).all())

    async def add_to_conversation(
        self, message: Message, conversation_id: uuid.UUID
    ) -> Message:
        if not await self._conversation_in_org(conversation_id):
            raise PermissionError(
                f"Conversation {conversation_id} is not in organization "
                f"{self.organization_id}."
            )
        message.conversation_id = conversation_id
        self.session.add(message)
        await self.session.flush()
        return message

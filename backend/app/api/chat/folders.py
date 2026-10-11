"""Conversation folders + public (unauthenticated) share endpoints (R1)."""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent
from app.database.models.conversation import Conversation
from app.database.models.conversation_folder import ConversationFolder
from app.database.models.message import Message
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.schemas.chat import (
    FolderCreate,
    FolderOut,
    FolderUpdate,
    PublicConversation,
    PublicMessage,
)
from app.services.agent_runtime import sender_to_role
from app.services.audit import audit

folders_router = APIRouter(prefix="/api/conversation-folders", tags=["chat-folders"])
public_chat_router = APIRouter(prefix="/api/public/conversations", tags=["chat-public"])


async def _folder_count(session: AsyncSession, folder_id: uuid.UUID) -> int:
    return int(
        await session.scalar(
            select(func.count(Conversation.id))
            .where(Conversation.folder_id == folder_id)
            .where(Conversation.deleted_at.is_(None))
        )
        or 0
    )


async def _to_out(session: AsyncSession, f: ConversationFolder) -> FolderOut:
    return FolderOut(
        id=f.id,
        name=f.name,
        color=f.color,
        icon=f.icon,
        conversation_count=await _folder_count(session, f.id),
        created_at=f.created_at,
        updated_at=f.updated_at,
    )


@folders_router.get("", response_model=list[FolderOut])
async def list_folders(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> list[FolderOut]:
    rows = list(
        (
            await session.scalars(
                select(ConversationFolder)
                .where(ConversationFolder.organization_id == ctx.organization_id)
                .where(ConversationFolder.user_id == ctx.user_id)
                .order_by(ConversationFolder.name.asc())
            )
        ).all()
    )
    return [await _to_out(session, f) for f in rows]


@folders_router.post("", response_model=FolderOut, status_code=status.HTTP_201_CREATED)
async def create_folder(
    payload: FolderCreate,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> FolderOut:
    folder = ConversationFolder(
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        name=payload.name.strip(),
        color=payload.color,
        icon=payload.icon,
    )
    session.add(folder)
    await session.commit()
    await session.refresh(folder)
    audit(
        "create",
        resource="conversation_folder",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        resource_id=str(folder.id),
        meta={"name": folder.name},
    )
    return await _to_out(session, folder)


async def _load_folder(
    session: AsyncSession, ctx: OrgContext, folder_id: uuid.UUID
) -> Optional[ConversationFolder]:
    return await session.scalar(
        select(ConversationFolder)
        .where(ConversationFolder.id == folder_id)
        .where(ConversationFolder.organization_id == ctx.organization_id)
        .where(ConversationFolder.user_id == ctx.user_id)
    )


@folders_router.put("/{folder_id}", response_model=FolderOut)
async def update_folder(
    folder_id: uuid.UUID,
    payload: FolderUpdate,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> FolderOut:
    folder = await _load_folder(session, ctx, folder_id)
    if folder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found.")
    if payload.name is not None:
        folder.name = payload.name.strip()
    if payload.color is not None:
        folder.color = payload.color
    if payload.icon is not None:
        folder.icon = payload.icon
    await session.commit()
    await session.refresh(folder)
    return await _to_out(session, folder)


@folders_router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
):
    folder = await _load_folder(session, ctx, folder_id)
    if folder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found.")
    # Detach conversations (don't delete them) before removing the folder.
    await session.execute(
        update(Conversation)
        .where(Conversation.folder_id == folder_id)
        .values(folder_id=None)
    )
    await session.delete(folder)
    await session.commit()
    audit(
        "delete",
        resource="conversation_folder",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        resource_id=str(folder_id),
    )
    return None


# ─────────────────── public, unauthenticated read ──────────────────

@public_chat_router.get("/{token}", response_model=PublicConversation)
async def public_conversation(
    token: str,
    session: AsyncSession = Depends(get_db),
) -> PublicConversation:
    """Read-only transcript view unlocked by a share token. No auth."""
    conv = await session.scalar(
        select(Conversation)
        .where(Conversation.share_token == token)
        .where(Conversation.deleted_at.is_(None))
    )
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Shared conversation not found.")

    agent_name = await session.scalar(
        select(Agent.name).where(Agent.id == conv.agent_id)
    )
    rows = list(
        (
            await session.scalars(
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.created_at.asc())
            )
        ).all()
    )
    return PublicConversation(
        title=conv.title,
        agent_name=agent_name,
        shared_at=conv.shared_at,
        messages=[
            PublicMessage(
                role=sender_to_role(m.sender),
                content=m.message,
                created_at=m.created_at,
            )
            for m in rows
        ],
    )

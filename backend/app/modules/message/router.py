"""消息 REST 路由：/api/messages/*。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.message.schemas import ReadRequest, SendMessageRequest
from app.modules.message.service import (
    get_messages,
    list_conversations,
    mark_read,
    send_message,
    unread_total,
)

router = APIRouter(prefix="/api/messages", tags=["message"])


@router.get("/conversations", response_model=ApiResponse[list])
async def conversations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = await list_conversations(db, str(user.id))
    return ApiResponse.ok(data=data)


@router.get("/conversations/{conversation_id}", response_model=ApiResponse[dict])
async def history(
    conversation_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = await get_messages(db, conversation_id, str(user.id), page=page, page_size=page_size)
    return ApiResponse.ok(data=data)


@router.post("/conversations/{conversation_id}/read", response_model=ApiResponse[dict])
async def read(
    conversation_id: str,
    body: ReadRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count = await mark_read(
        db,
        conversation_id=conversation_id,
        user_id=str(user.id),
        last_read_message_id=body.last_read_message_id,
    )
    return ApiResponse.ok(data={"marked": count})


@router.get("/unread", response_model=ApiResponse[dict])
async def unread(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total = await unread_total(db, str(user.id))
    return ApiResponse.ok(data={"unread": total})

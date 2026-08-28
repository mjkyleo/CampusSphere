"""消息业务逻辑：会话、消息、已读、未读计数。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.utils import Page, PageResult
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.modules.message.models import Conversation, Message, Participant

_logger = get_logger("message.service")


async def create_conversation(
    db: AsyncSession,
    *,
    conv_type: str = "direct",
    participant_ids: list[str],
    related_id: Optional[str] = None,
    creator_id: Optional[str] = None,
) -> Conversation:
    """创建会话并添加参与者（去重）。"""
    if conv_type == "direct" and related_id is None and len(participant_ids) == 2:
        # 单聊幂等：已存在则复用
        a, b = participant_ids
        existing = await db.scalar(
            select(Conversation)
            .where(Conversation.conv_type == "direct")
            .join(Participant, Participant.conversation_id == Conversation.id)
            .where(Participant.user_id.in_([a, b]))
            .group_by(Conversation.id)
            .having(func.count(Participant.id) == 2)
        )
        if existing:
            return existing
    conv = Conversation(conv_type=conv_type, related_id=related_id)
    db.add(conv)
    await db.flush()
    for uid in set(participant_ids):
        db.add(Participant(conversation_id=str(conv.id), user_id=uid))
    await db.commit()
    await db.refresh(conv)
    return conv


async def list_conversations(db: AsyncSession, user_id: str) -> list[dict]:
    stmt = (
        select(Conversation)
        .join(Participant, Participant.conversation_id == Conversation.id)
        .where(Participant.user_id == user_id)
        .order_by(Conversation.created_at.desc())
    )
    convs = (await db.scalars(stmt)).all()
    result = []
    for c in convs:
        participants = (await db.scalars(
            select(Participant).where(Participant.conversation_id == str(c.id))
        )).all()
        last_msg = await db.scalar(
            select(Message)
            .where(Message.conversation_id == str(c.id))
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        unread = await db.scalar(
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == str(c.id),
                Message.sender_id != user_id,
                Message.is_read.is_(False),
            )
        )
        result.append({
            "id": str(c.id),
            "conv_type": c.conv_type,
            "related_id": c.related_id,
            "participants": [{"user_id": p.user_id, "last_read_at": p.last_read_at.isoformat() if p.last_read_at else None} for p in participants],
            "last_message": MessageOut_wrap(last_msg),
            "unread_count": int(unread or 0),
        })
    return result


def MessageOut_wrap(msg: Optional[Message]) -> Optional[dict]:
    if not msg:
        return None
    return {
        "id": str(msg.id),
        "conversation_id": msg.conversation_id,
        "sender_id": msg.sender_id,
        "type": msg.type,
        "content": msg.content,
        "is_read": msg.is_read,
        "created_at": msg.created_at.isoformat() if msg.created_at else "",
    }


async def get_messages(
    db: AsyncSession, conversation_id: str, user_id: str, page: int = 1, page_size: int = 50
) -> dict:
    # 权限校验：必须是参与者
    part = await db.scalar(
        select(Participant).where(
            Participant.conversation_id == conversation_id, Participant.user_id == user_id
        )
    )
    if not part:
        raise BizError(ErrorCode.FORBIDDEN, "无权访问该会话")
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.scalars(stmt)).all()
    total = await db.scalar(
        select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)
    )
    items = [
        {
            "id": str(m.id),
            "conversation_id": m.conversation_id,
            "sender_id": m.sender_id,
            "type": m.type,
            "content": m.content,
            "is_read": m.is_read,
            "created_at": m.created_at.isoformat() if m.created_at else "",
        }
        for m in rows
    ]
    page_obj = Page(page=page, page_size=page_size)
    return PageResult(items=items, total=total or 0, page=page, page_size=page_size).to_dict()


async def send_message(
    db: AsyncSession,
    *,
    conversation_id: str,
    sender_id: str,
    type: int = 0,
    content: str = "",
) -> Message:
    part = await db.scalar(
        select(Participant).where(
            Participant.conversation_id == conversation_id, Participant.user_id == sender_id
        )
    )
    if not part:
        raise BizError(ErrorCode.FORBIDDEN, "非会话成员")
    msg = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        type=type,
        content=content,
        is_read=False,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def mark_read(
    db: AsyncSession,
    *,
    conversation_id: str,
    user_id: str,
    last_read_message_id: Optional[str] = None,
) -> int:
    """标记某会话中发给自己的消息为已读，更新已读游标。返回标记数。"""
    part = await db.scalar(
        select(Participant).where(
            Participant.conversation_id == conversation_id, Participant.user_id == user_id
        )
    )
    if not part:
        raise BizError(ErrorCode.FORBIDDEN, "非会话成员")
    stmt = select(Message).where(
        Message.conversation_id == conversation_id,
        Message.sender_id != user_id,
        Message.is_read.is_(False),
    )
    if last_read_message_id:
        target = await db.get(Message, last_read_message_id)
        if target:
            stmt = stmt.where(Message.created_at <= target.created_at)
    rows = (await db.scalars(stmt)).all()
    count = 0
    for m in rows:
        m.is_read = True
        count += 1
    part.last_read_at = datetime.now(timezone.utc)
    await db.commit()
    return count


async def unread_total(db: AsyncSession, user_id: str) -> int:
    conv_ids = (
        await db.scalars(
            select(Participant.conversation_id).where(Participant.user_id == user_id)
        )
    ).all()
    if not conv_ids:
        return 0
    total = await db.scalar(
        select(func.count())
        .select_from(Message)
        .where(
            Message.conversation_id.in_(conv_ids),
            Message.sender_id != user_id,
            Message.is_read.is_(False),
        )
    )
    return int(total or 0)

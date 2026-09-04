"""消息业务逻辑：会话、消息、已读、未读计数。"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.utils import PageResult
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.modules.message.models import Conversation, Message, Participant

_logger = get_logger("message.service")


async def create_conversation(
    db: AsyncSession,
    *,
    conv_type: str = "direct",
    participant_ids: list[str],
    related_id: str | None = None,
    creator_id: str | None = None,
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
    """列出某用户的会话列表（含参与者 / 最后一条消息 / 未读数）。

    性能：旧实现对每个会话再发 3 条查询（participants / last_message /
    unread），会话多时是典型 N+1（O(3N+1)）。这里改为 4 条批量查询：

    1. 拉会话（带入 participants，一次 JOIN 取回）；
    2. 用窗口函数一次性取每个会话的"最后一条消息"；
    3. 用 ``GROUP BY`` 一次性取每个会话的未读计数。

    无论会话数量多少，固定 ~4 条 SQL，列表接口随会话数线性膨胀的问题消除。
    """
    convs = (
        await db.scalars(
            select(Conversation)
            .join(Participant, Participant.conversation_id == Conversation.id)
            .where(Participant.user_id == user_id)
            .order_by(Conversation.created_at.desc())
        )
    ).all()
    if not convs:
        return []

    conv_ids = [str(c.id) for c in convs]

    # 批量取参与者，按会话归组
    parts = (
        await db.scalars(
            select(Participant).where(Participant.conversation_id.in_(conv_ids))
        )
    ).all()
    parts_by_conv: dict[str, list] = {}
    for p in parts:
        parts_by_conv.setdefault(p.conversation_id, []).append(p)

    # 窗口函数取每个会话的最后一条消息（created_at 倒序第 1 行）
    rn = func.row_number().over(
        partition_by=Message.conversation_id, order_by=Message.created_at.desc()
    ).label("rn")
    last_stmt = select(Message, rn).where(Message.conversation_id.in_(conv_ids))
    last_rows = (await db.execute(last_stmt)).all()
    last_msgs = [m for m, r in last_rows if r == 1]
    msg_by_conv = {m.conversation_id: m for m in last_msgs}

    # 批量取未读计数（别人发的、未读），GROUP BY 会话
    unread_rows = (
        await db.execute(
            select(Message.conversation_id, func.count())
            .where(
                Message.conversation_id.in_(conv_ids),
                Message.sender_id != user_id,
                Message.is_read.is_(False),
            )
            .group_by(Message.conversation_id)
        )
    ).all()
    unread_by_conv = {str(cid): int(cnt) for cid, cnt in unread_rows}

    result = []
    for c in convs:
        cid = str(c.id)
        participants = parts_by_conv.get(cid, [])
        result.append({
            "id": cid,
            "conv_type": c.conv_type,
            "related_id": c.related_id,
            "participants": [
                {
                    "user_id": p.user_id,
                    "last_read_at": p.last_read_at.isoformat() if p.last_read_at else None,
                }
                for p in participants
            ],
            "last_message": MessageOut_wrap(msg_by_conv.get(cid)),
            "unread_count": unread_by_conv.get(cid, 0),
        })
    return result


def MessageOut_wrap(msg: Message | None) -> dict | None:
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
    last_read_message_id: str | None = None,
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
    part.last_read_at = datetime.now(UTC)
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

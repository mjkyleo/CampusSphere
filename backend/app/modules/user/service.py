"""用户模块业务逻辑。"""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.utils import mask_email, mask_phone
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.user.models import UserProfile

_logger = get_logger("user.service")


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise BizError(ErrorCode.NOT_FOUND, "用户不存在")
    return user


async def get_profile(db: AsyncSession, user: User) -> UserProfile:
    profile = await db.scalar(
        select(UserProfile).where(UserProfile.user_id == str(user.id))
    )
    if not profile:
        profile = UserProfile(user_id=str(user.id))
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


async def update_profile(
    db: AsyncSession, user: User, data
) -> UserProfile:
    profile = await get_profile(db, user)
    if data.nickname is not None:
        user.nickname = data.nickname
    if data.avatar is not None:
        user.avatar = data.avatar
    if data.bio is not None:
        profile.bio = data.bio
    if data.school_major is not None:
        profile.school_major = data.school_major
    if data.grade is not None:
        profile.grade = data.grade
    await db.commit()
    await db.refresh(profile)
    return profile


async def list_users(db: AsyncSession, q: str = "", page: int = 1, page_size: int = 20):
    """用户列表（搜索最终接 Meilisearch，此处 DB 模糊匹配兜底）。"""
    stmt = select(User).where(User.deleted_at.is_(None))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.username.ilike(like), User.nickname.ilike(like)))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.scalars(stmt)).all()
    items = [
        {
            "id": str(u.id),
            "username": u.username,
            "nickname": u.nickname,
            "avatar": u.avatar,
            "email": mask_email(u.email),
            "phone": mask_phone(u.phone),
            "status": u.status,
        }
        for u in rows
    ]
    return {"items": items, "total": total or 0, "page": page, "page_size": page_size}


async def search_users(db: AsyncSession, q: str, limit: int = 20):
    """搜索用户（优先 Meilisearch，失败回退 DB）。"""
    try:
        from app.search.client import search_client

        if search_client and search_client.enabled:
            hits = await search_client.search("users", q, limit=limit)
            return hits
    except Exception as exc:  # noqa: BLE001
        _logger.warning("meili_search_fallback", error=str(exc))
    return (await list_users(db, q=q, page_size=limit))["items"]

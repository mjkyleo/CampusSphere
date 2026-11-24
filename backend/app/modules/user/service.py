"""用户模块业务逻辑。"""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.utils import escape_like, mask_email, mask_phone
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
    if data.campus is not None:
        profile.campus = data.campus
    if data.contact_wx is not None:
        profile.contact_wx = data.contact_wx
    if data.grade is not None:
        profile.grade = data.grade
    await db.commit()
    await db.refresh(profile)
    # 同步用户搜索索引（最佳努力，见 app/search/sync.py）
    from app.search import sync as search_sync

    search_sync.index_user(user)
    return profile


async def list_users(db: AsyncSession, q: str = "", page: int = 1, page_size: int = 20):
    """用户列表（搜索最终接 Meilisearch，此处 DB 模糊匹配兜底）。"""
    stmt = select(User).where(User.deleted_at.is_(None))
    if q:
        like = f"%{escape_like(q)}%"
        stmt = stmt.where(or_(User.username.ilike(like, escape="\\"), User.nickname.ilike(like, escape="\\")))
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
    except Exception as exc:
        _logger.warning("meili_search_fallback", error=str(exc))
    return (await list_users(db, q=q, page_size=limit))["items"]


# ---------------------------------------------------------------------------
# 物品收藏（P2-22：此前前端收藏是纯 toast 假动作，无任何落库）
# ---------------------------------------------------------------------------
async def list_favorites(db: AsyncSession, user: User) -> list[dict]:
    """当前用户的收藏列表（含物品详情，剔除已删除物品）。"""
    from app.modules.item.models import Item
    from app.modules.item.schemas import ItemOut
    from app.modules.user.models import UserFavorite

    rows = (
        await db.scalars(
            select(Item)
            .join(UserFavorite, UserFavorite.item_id == Item.id)
            .where(UserFavorite.user_id == str(user.id), Item.deleted_at.is_(None))
            .options(selectinload(Item.images))
            .order_by(UserFavorite.created_at.desc())
        )
    ).all()
    return [ItemOut.model_validate(i).model_dump() for i in rows]


async def add_favorite(db: AsyncSession, user: User, item_id: str) -> None:
    from sqlalchemy.exc import IntegrityError

    from app.core.cache import invalidate_namespace
    from app.modules.item.models import Item
    from app.modules.user.models import UserFavorite

    item = await db.get(Item, item_id)
    if not item or item.deleted_at is not None:
        raise BizError(ErrorCode.NOT_FOUND, "物品不存在")
    if str(item.owner_id) == str(user.id):
        raise BizError(ErrorCode.CONFLICT, "不能收藏自己发布的物品")
    db.add(UserFavorite(user_id=str(user.id), item_id=str(item.id)))
    try:
        await db.commit()
    except IntegrityError:
        # 并发双击由 uq_user_favorite 兜底：已收藏视作成功（幂等语义）
        await db.rollback()
        _logger.info("favorite_duplicate_ignored", user_id=str(user.id), item_id=item_id)
        return
    await invalidate_namespace("items")


async def remove_favorite(db: AsyncSession, user: User, item_id: str) -> None:
    from app.modules.user.models import UserFavorite

    fav = await db.scalar(
        select(UserFavorite).where(
            UserFavorite.user_id == str(user.id), UserFavorite.item_id == str(item_id)
        )
    )
    if not fav:
        raise BizError(ErrorCode.NOT_FOUND, "该物品不在收藏中")
    await db.delete(fav)
    await db.commit()

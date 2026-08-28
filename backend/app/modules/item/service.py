"""二手物品业务逻辑。"""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums import ItemStatus, TradeStatus
from app.core.cache import NULL_SENTINEL, cache_get_json, cache_set_json, invalidate_namespace
from app.core.config import settings
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.modules.admin.models import AppConfig
from app.modules.auth.models import User
from app.modules.item.models import Item, ItemImage, TradeSession
from app.modules.item.schemas import ItemCreate, ItemUpdate
from app.modules.item.statemachine import validate_transition

_logger = get_logger("item.service")

_ITEM_REVIEW_KEY = "item.review"


async def _item_review_enabled(db: AsyncSession) -> bool:
    """发布审核开关：DB（后台配置）优先，缺省回退 school.yaml 的 items.review.enabled。"""
    default = bool(((settings.items or {}).get("review") or {}).get("enabled", False))
    cfg = await db.scalar(select(AppConfig).where(AppConfig.key == _ITEM_REVIEW_KEY))
    if not cfg:
        return default
    return bool(cfg.value.get("enabled", default))


async def create_item(db: AsyncSession, owner: User, data: ItemCreate) -> Item:
    # 审核开关开启时新发布进入"待审核(PENDING)"，否则直接上架
    status = ItemStatus.PENDING.value if await _item_review_enabled(db) else ItemStatus.ON_SALE.value
    item = Item(
        owner_id=str(owner.id),
        title=data.title,
        description=data.description,
        price=data.price,
        category=data.category,
        status=status,
    )
    for img in data.images:
        item.images.append(
            ItemImage(object_key=img.object_key, sort_order=img.sort_order)
        )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    # 写操作：整体失效「物品列表」缓存，避免新发布不立即可见
    await invalidate_namespace("items")
    _logger.info("item_created", item_id=str(item.id), owner=str(owner.id))
    return item


async def list_items(
    db: AsyncSession,
    *,
    keyword: str = "",
    category: str = "",
    status: int | None = None,
    owner_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    # 热点列表：先查缓存（防穿透/雪崩策略见 app/core/cache.py）
    cached = await cache_get_json(
        "items",
        keyword=keyword,
        category=category,
        status=status,
        owner_id=owner_id,
        page=page,
        page_size=page_size,
    )
    if cached is not None:
        if cached is NULL_SENTINEL:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}
        return cached

    stmt = select(Item).where(Item.deleted_at.is_(None))
    if keyword:
        stmt = stmt.where(Item.title.ilike(f"%{keyword}%"))
    if category:
        stmt = stmt.where(Item.category == category)
    if status is not None:
        stmt = stmt.where(Item.status == status)
    if owner_id:
        stmt = stmt.where(Item.owner_id == owner_id)
    else:
        # 广场浏览：永远排除"待审核(PENDING)"，避免审核中的物品泄露；
        # 即使显式传 status=4，也会因 status==4 与 status!=4 冲突而查不到。
        stmt = stmt.where(Item.status != ItemStatus.PENDING.value)
    total = await db.scalar(
        select(func.count()).select_from(stmt.subquery())
    )
    # N+1 修复：列表序列化会访问 item.images（逐物品再查一次）-> 一次性 selectinload 加载
    rows = (
        await db.scalars(
            stmt.order_by(Item.created_at.desc())
            .options(selectinload(Item.images))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    items = [
        {
            "id": str(i.id),
            "owner_id": i.owner_id,
            "title": i.title,
            "description": i.description,
            "price": i.price,
            "category": i.category,
            "status": i.status,
            "images": [{"object_key": im.object_key, "sort_order": im.sort_order} for im in i.images],
            "created_at": i.created_at.isoformat() if i.created_at else "",
        }
        for i in rows
    ]
    result = {"items": items, "total": total or 0, "page": page, "page_size": page_size}
    await cache_set_json(
        "items",
        result,
        keyword=keyword,
        category=category,
        status=status,
        owner_id=owner_id,
        page=page,
        page_size=page_size,
    )
    return result


async def get_item(db: AsyncSession, item_id: str) -> Item:
    # N+1 修复：详情序列化 ItemOut 含 images 关系，避免访问时再发一次查询
    stmt = (
        select(Item)
        .where(Item.id == item_id, Item.deleted_at.is_(None))
        .options(selectinload(Item.images))
    )
    item = (await db.scalars(stmt)).first()
    if not item:
        raise BizError(ErrorCode.NOT_FOUND, "物品不存在")
    return item


async def update_item(db: AsyncSession, item: Item, data: ItemUpdate) -> Item:
    if data.title is not None:
        item.title = data.title
    if data.description is not None:
        item.description = data.description
    if data.price is not None:
        item.price = data.price
    if data.category is not None:
        item.category = data.category
    if data.status is not None and data.status != item.status:
        validate_transition(item.status, data.status)
        item.status = data.status
    await db.commit()
    await db.refresh(item)
    # 写操作：失效物品列表缓存（状态/标题变更会影响广场展示）
    await invalidate_namespace("items")
    return item


async def delete_item(db: AsyncSession, item: Item) -> None:
    await db.delete(item)
    await db.commit()
    # 写操作：失效物品列表缓存
    await invalidate_namespace("items")


async def create_trade_session(
    db: AsyncSession, item: Item, buyer: User
) -> TradeSession:
    if item.status != ItemStatus.ON_SALE.value:
        raise BizError(ErrorCode.CONFLICT, "该物品当前不可交易")
    # 创建交易会话（并联动消息模块生成会话）
    ts = TradeSession(
        item_id=str(item.id),
        buyer_id=str(buyer.id),
        seller_id=item.owner_id,
        status=TradeStatus.PENDING.value,
    )
    db.add(ts)
    await db.commit()
    await db.refresh(ts)

    from app.modules.message.service import create_conversation

    conv = await create_conversation(
        db,
        conv_type="trade",
        related_id=str(ts.id),
        participant_ids=[str(buyer.id), item.owner_id],
        creator_id=str(buyer.id),
    )
    ts.conversation_id = str(conv.id)
    await db.commit()
    await db.refresh(ts)
    _logger.info("trade_session_created", trade_id=str(ts.id), conv=str(conv.id))
    return ts

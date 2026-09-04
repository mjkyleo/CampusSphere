"""二手物品业务逻辑。"""

from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
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


async def cas_item_status(
    db: AsyncSession,
    item_id: str,
    expected: int,
    target: int,
    *,
    message: str = "物品状态已被其他操作变更，请刷新后重试",
) -> None:
    """条件 UPDATE（Compare-And-Swap）原子变更物品状态。

    把「读状态 → 判断 → 写状态」三步合成一条 SQL：

    ``UPDATE items SET status=:target WHERE id=:id AND status=:expected``

    受影响行数为 1 表示抢占成功；为 0 说明在本次请求执行期间已经有别的
    请求改过这条记录（并发抢购 / 重复提交 / 管理后台介入），此时直接判负，
    由调用方转成 409 交给前端提示用户刷新。

    SQLite 与 PostgreSQL 下语义一致，故作为主实现，无需再按数据库分支。
    """
    result = await db.execute(
        update(Item)
        .where(Item.id == item_id, Item.status == expected)
        .values(status=target)
    )
    if result.rowcount != 1:
        _logger.info(
            "item_status_cas_failed", item_id=item_id, expected=expected, target=target
        )
        raise BizError(ErrorCode.CONFLICT, message)


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
        # 先把上面已改字段落盘，再对 status 走条件 UPDATE：
        # 两者分开执行，避免 ORM 的整行 UPDATE 覆盖掉 CAS 的条件判断。
        await db.flush()
        await cas_item_status(db, str(item.id), item.status, data.status)
        await db.refresh(item)
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
    if str(item.owner_id) == str(buyer.id):
        raise BizError(ErrorCode.CONFLICT, "不能与自己发布的物品发起交易")
    if item.status != ItemStatus.ON_SALE.value:
        raise BizError(ErrorCode.CONFLICT, "该物品当前不可交易")

    # 并发抢占：用「带旧状态条件的 UPDATE」把 ON_SALE 原子改为 RESERVED。
    #
    # 为什么不能只靠上面的 if 判断：check-then-act 之间存在时间窗。两个买家
    # 同时点"我想要"时，双方都能读到 ON_SALE，随后各自建出一个活跃会话，
    # 同一物品被卖两次。条件 UPDATE 把判断与写入合成一步，数据库保证只有
    # 一个请求能把 rowcount 变成 1，另一个读到 0 即判负。
    #
    # 状态抢占 + 会话创建放在同一事务：任一步失败整体回滚，物品不会卡在
    # RESERVED 却没有会话的"僵尸"状态。
    try:
        await cas_item_status(
            db,
            str(item.id),
            ItemStatus.ON_SALE.value,
            ItemStatus.RESERVED.value,
            message="该物品已被其他同学抢先预订，看看别的闲置吧",
        )
        ts = TradeSession(
            item_id=str(item.id),
            buyer_id=str(buyer.id),
            seller_id=item.owner_id,
            status=TradeStatus.PENDING.value,
        )
        db.add(ts)
        await db.flush()

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
    except IntegrityError as exc:
        # 部分唯一索引兜底：同一物品已存在进行中的会话（理论上 CAS 已拦截，
        # 此处防御索引与 CAS 判定不一致的极端情况，如管理员手工改状态）。
        await db.rollback()
        _logger.warning("trade_session_conflict", item_id=str(item.id), error=str(exc))
        raise BizError(ErrorCode.CONFLICT, "该物品已有进行中的交易，无法重复发起") from exc
    except Exception:
        await db.rollback()
        raise

    await db.refresh(ts)
    await db.refresh(item)
    # 状态已变更，列表缓存需立即失效，否则广场上仍显示"在售"
    await invalidate_namespace("items")
    _logger.info("trade_session_created", trade_id=str(ts.id), conv=str(conv.id))
    return ts

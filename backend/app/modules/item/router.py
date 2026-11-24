"""二手物品路由：/api/items/*。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ItemStatus
from app.core.database import get_db
from app.core.deps import Principal, Scope, require_owner_or_scope, require_scope
from app.core.exceptions import BizError, ErrorCode
from app.core.response import ApiResponse
from app.modules.auth.deps import get_current_user, get_current_user_optional
from app.modules.auth.models import User
from app.modules.item.schemas import ItemCreate, ItemOut, ItemUpdate, TradeSessionOut
from app.modules.item.service import (
    cancel_trade,
    complete_trade,
    create_item,
    create_trade_session,
    delete_item,
    get_item,
    get_trade,
    list_items,
    update_item,
)

router = APIRouter(prefix="/api/items", tags=["item"])


@router.post("", response_model=ApiResponse[ItemOut])
async def create(
    data: ItemCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = await create_item(db, user, data)
    return ApiResponse.ok(data=ItemOut.model_validate(item))


@router.get("", response_model=ApiResponse[dict])
async def list_all(
    keyword: str = Query(default=""),
    category: str = Query(default=""),
    status: int = Query(default=None),
    owner_id: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await list_items(
        db, keyword=keyword, category=category,
        status=status if status is not None else None,
        owner_id=owner_id,
        page=page, page_size=page_size,
    )
    return ApiResponse.ok(data=result)


@router.get("/search", response_model=ApiResponse[list])
async def search(
    q: str = Query(default="", min_length=1),
    # P3：limit 此前缺 ge=1，Postgres 下 LIMIT -1/0 会 500；负值同样拒绝
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from app.search.client import search_client

    if search_client and search_client.enabled:
        hits = await search_client.search("items", q, limit=limit)
        # 索引中理论上只保留在售物品，但防御性地再过滤一次，
        # 避免异步任务延迟/异常时返回未审核或已下架的物品。
        hits = [h for h in hits if h.get("status") == ItemStatus.ON_SALE.value]
        return ApiResponse.ok(data=hits)
    result = await list_items(db, keyword=q, page_size=limit)
    return ApiResponse.ok(data=result["items"])

# NOTE: 必须声明在 /{item_id} 之前，否则 "categories" 会被当作 item_id 匹配
@router.get("/categories", response_model=ApiResponse[dict])
async def categories(db: AsyncSession = Depends(get_db)):
    """公开读取二手交易分类（后台配置，含 school.yaml 兜底）。"""
    from app.modules.admin.service import get_item_categories

    return ApiResponse.ok(data={"categories": await get_item_categories(db)})


@router.get("/{item_id}", response_model=ApiResponse[ItemOut])
async def detail(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    item = await get_item(db, item_id)
    # 待审核(PENDING)物品仅本人可见，其他人一律视为不存在
    if item.status == ItemStatus.PENDING.value and (not user or str(item.owner_id) != str(user.id)):
        raise BizError(ErrorCode.NOT_FOUND, "物品不存在")
    return ApiResponse.ok(data=ItemOut.model_validate(item))


@router.patch("/{item_id}", response_model=ApiResponse[ItemOut])
async def update(
    item_id: str,
    data: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_scope(Scope.WRITE)),
):
    item = await get_item(db, item_id)
    require_owner_or_scope(item.owner_id, principal, Scope.ADMIN)
    # P1-1：开启审核后新物品为 PENDING，状态机允许 PENDING → ON_SALE/OFF_SHELF，
    # 该出口仅供管理员审核使用（admin.service.approve/reject_item 走独立路径）。
    # 若不拦，发布者可直接 PATCH status 自审上架，还能与管理员审核竞争（先抢先赢）。
    if (
        item.status == ItemStatus.PENDING.value
        and data.status is not None
        and data.status != item.status
        and not principal.has(Scope.ADMIN)
    ):
        raise BizError(ErrorCode.FORBIDDEN, "待审核物品的状态需由管理员审核后变更")
    item = await update_item(db, item, data)
    return ApiResponse.ok(data=ItemOut.model_validate(item))


@router.delete("/{item_id}", response_model=ApiResponse[None])
async def delete(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_scope(Scope.WRITE)),
):
    """删除物品：本人（write）或管理员（admin）可删。

    权限判定完全由 ``require_scope`` + ``require_owner_or_scope`` 表达，
    Service 层的 ``delete_item`` 只负责删除，不知道"管理员"这个概念的存在。
    """
    item = await get_item(db, item_id)
    require_owner_or_scope(item.owner_id, principal, Scope.ADMIN)
    await delete_item(db, item)
    return ApiResponse.ok(message="已删除")


@router.post("/{item_id}/trade", response_model=ApiResponse[TradeSessionOut])
async def trade(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = await get_item(db, item_id)
    ts = await create_trade_session(db, item, user)
    return ApiResponse.ok(data=TradeSessionOut.model_validate(ts))


# ---------------------------------------------------------------------------
# 交易会话生命周期（P2-1）：此前会话创建后永不变更，RESERVED 物品被
# 重新上架后部分唯一索引让所有新抢占 409，无解困路径。
# NOTE: /trades/* 为两段路径，不会与 /{item_id} 单段匹配冲突。
# ---------------------------------------------------------------------------
@router.post("/trades/{trade_id}/complete", response_model=ApiResponse[TradeSessionOut])
async def trade_complete(
    trade_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """交易双方确认完成：会话 → COMPLETED，物品 → SOLD。"""
    ts = await complete_trade(db, await get_trade(db, trade_id), user)
    return ApiResponse.ok(data=TradeSessionOut.model_validate(ts))


@router.post("/trades/{trade_id}/cancel", response_model=ApiResponse[TradeSessionOut])
async def trade_cancel(
    trade_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """交易双方取消：会话 → CANCELLED，物品释放回 ON_SALE。"""
    ts = await cancel_trade(db, await get_trade(db, trade_id), user)
    return ApiResponse.ok(data=TradeSessionOut.model_validate(ts))

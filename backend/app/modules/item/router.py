"""二手物品路由：/api/items/*。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.common.enums import ItemStatus
from app.core.exceptions import BizError, ErrorCode
from app.core.response import ApiResponse
from app.modules.auth.deps import get_current_user, get_current_user_optional, require_owner
from app.modules.auth.models import User
from app.modules.item.schemas import ItemCreate, ItemOut, ItemUpdate, TradeSessionOut
from app.modules.item.service import (
    create_item,
    create_trade_session,
    delete_item,
    get_item,
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
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await list_items(
        db, keyword=keyword, category=category,
        status=status if status is not None else None,
        page=page, page_size=page_size,
    )
    return ApiResponse.ok(data=result)


@router.get("/search", response_model=ApiResponse[list])
async def search(
    q: str = Query(default="", min_length=1),
    limit: int = Query(default=20, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from app.search.client import search_client

    if search_client and search_client.enabled:
        hits = await search_client.search("items", q, limit=limit)
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
    user: User = Depends(get_current_user),
):
    item = await get_item(db, item_id)
    require_owner(item.owner_id, user)
    item = await update_item(db, item, data)
    return ApiResponse.ok(data=ItemOut.model_validate(item))


@router.delete("/{item_id}", response_model=ApiResponse[None])
async def delete(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = await get_item(db, item_id)
    require_owner(item.owner_id, user)
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

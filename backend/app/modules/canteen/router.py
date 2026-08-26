"""食堂路由：/api/canteens/*。

- 公开读取：列表 / 详情 / 菜品详情 / 评价
- 写操作（创建/修改/删除）统一走管理端 /api/admin/canteens/*，
  普通用户无法直接创建食堂、摊位、菜品。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.canteen.schemas import (
    CanteenOut,
    CanteenReviewCreate,
    CanteenReviewOut,
    DishOut,
)
from app.modules.canteen.service import (
    add_review,
    get_canteen,
    get_dish,
    list_canteens,
    list_reviews,
)

router = APIRouter(prefix="/api/canteens", tags=["canteen"])


@router.get("", response_model=ApiResponse[list])
async def list_all(db: AsyncSession = Depends(get_db)):
    return ApiResponse.ok(data=await list_canteens(db))


@router.get("/dishes/{dish_id}", response_model=ApiResponse[dict])
async def dish_detail(dish_id: str, db: AsyncSession = Depends(get_db)):
    dish = await get_dish(db, dish_id)
    reviews = await list_reviews(db, dish_id)
    return ApiResponse.ok(data={"dish": DishOut.model_validate(dish).model_dump(), "reviews": reviews})


@router.post("/dishes/{dish_id}/reviews", response_model=ApiResponse[CanteenReviewOut])
async def review(dish_id: str, data: CanteenReviewCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    dish = await get_dish(db, dish_id)
    r = await add_review(db, dish, user, data)
    return ApiResponse.ok(data=CanteenReviewOut.model_validate(r))


# 公开详情（声明在最后，避免影响 /dishes/ 前缀端点）
@router.get("/{canteen_id}", response_model=ApiResponse[CanteenOut])
async def detail(canteen_id: str, db: AsyncSession = Depends(get_db)):
    return ApiResponse.ok(data=CanteenOut.model_validate(await get_canteen(db, canteen_id)))

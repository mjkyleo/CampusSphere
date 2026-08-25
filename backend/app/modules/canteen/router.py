"""食堂路由：/api/canteens/*。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.canteen.schemas import (
    CanteenCreate,
    CanteenOut,
    CanteenReviewCreate,
    CanteenReviewOut,
    DishCreate,
    DishOut,
    StallCreate,
    StallOut,
)
from app.modules.canteen.service import (
    add_review,
    create_canteen,
    create_dish,
    create_stall,
    get_dish,
    list_canteens,
    list_reviews,
)

router = APIRouter(prefix="/api/canteens", tags=["canteen"])


@router.get("", response_model=ApiResponse[list])
async def list_all(db: AsyncSession = Depends(get_db)):
    return ApiResponse.ok(data=await list_canteens(db))


@router.post("", response_model=ApiResponse[CanteenOut])
async def create(data: CanteenCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return ApiResponse.ok(data=CanteenOut.model_validate(await create_canteen(db, data)))


@router.post("/stalls", response_model=ApiResponse[StallOut])
async def create_stall_endpoint(data: StallCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return ApiResponse.ok(data=StallOut.model_validate(await create_stall(db, data)))


@router.post("/dishes", response_model=ApiResponse[DishOut])
async def create_dish_endpoint(data: DishCreate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return ApiResponse.ok(data=DishOut.model_validate(await create_dish(db, data)))


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

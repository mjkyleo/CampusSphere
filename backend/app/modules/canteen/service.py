"""食堂业务逻辑。"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizError, ErrorCode
from app.modules.auth.models import User
from app.modules.canteen.models import (
    Canteen,
    CanteenReview,
    Dish,
    Stall,
)
from app.modules.canteen.schemas import (
    CanteenCreate,
    CanteenOut,
    CanteenReviewCreate,
    CanteenReviewOut,
    DishCreate,
    StallCreate,
)


async def list_canteens(db: AsyncSession) -> list:
    rows = (await db.scalars(select(Canteen).order_by(Canteen.created_at.desc()))).all()
    return [CanteenOut.model_validate(c).model_dump() for c in rows]


async def create_canteen(db: AsyncSession, data: CanteenCreate) -> Canteen:
    c = Canteen(**data.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def create_stall(db: AsyncSession, data: StallCreate) -> Stall:
    canteen = await db.get(Canteen, data.canteen_id)
    if not canteen:
        raise BizError(ErrorCode.NOT_FOUND, "食堂不存在")
    s = Stall(canteen_id=data.canteen_id, name=data.name)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def create_dish(db: AsyncSession, data: DishCreate) -> Dish:
    stall = await db.get(Stall, data.stall_id)
    if not stall:
        raise BizError(ErrorCode.NOT_FOUND, "摊位不存在")
    d = Dish(stall_id=data.stall_id, name=data.name, price=data.price)
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


async def get_dish(db: AsyncSession, dish_id: str) -> Dish:
    d = await db.get(Dish, dish_id)
    if not d:
        raise BizError(ErrorCode.NOT_FOUND, "菜品不存在")
    return d


async def add_review(db: AsyncSession, dish: Dish, user: User, data: CanteenReviewCreate) -> CanteenReview:
    r = CanteenReview(
        dish_id=str(dish.id), user_id=str(user.id),
        rating=data.rating, content=data.content,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


async def list_reviews(db: AsyncSession, dish_id: str) -> list:
    rows = (await db.scalars(
        select(CanteenReview).where(CanteenReview.dish_id == dish_id).order_by(CanteenReview.created_at.desc())
    )).all()
    return [CanteenReviewOut.model_validate(r).model_dump() for r in rows]

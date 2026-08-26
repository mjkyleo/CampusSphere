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


async def get_canteen(db: AsyncSession, canteen_id: str) -> Canteen:
    c = await db.get(Canteen, canteen_id)
    if not c:
        raise BizError(ErrorCode.NOT_FOUND, "食堂不存在")
    return c


async def update_canteen(db: AsyncSession, canteen_id: str, data: CanteenCreate) -> Canteen:
    c = await get_canteen(db, canteen_id)
    c.name = data.name
    c.location = data.location
    c.image = data.image
    await db.commit()
    await db.refresh(c)
    return c


async def delete_canteen(db: AsyncSession, canteen_id: str) -> None:
    c = await get_canteen(db, canteen_id)
    await db.delete(c)
    await db.commit()


async def create_stall(db: AsyncSession, data: StallCreate) -> Stall:
    canteen = await db.get(Canteen, data.canteen_id)
    if not canteen:
        raise BizError(ErrorCode.NOT_FOUND, "食堂不存在")
    s = Stall(canteen_id=data.canteen_id, name=data.name, image=data.image)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def update_stall(db: AsyncSession, stall_id: str, data: StallCreate) -> Stall:
    s = await db.get(Stall, stall_id)
    if not s:
        raise BizError(ErrorCode.NOT_FOUND, "摊位不存在")
    s.name = data.name
    s.image = data.image
    await db.commit()
    await db.refresh(s)
    return s


async def delete_stall(db: AsyncSession, stall_id: str) -> None:
    s = await db.get(Stall, stall_id)
    if not s:
        raise BizError(ErrorCode.NOT_FOUND, "摊位不存在")
    await db.delete(s)
    await db.commit()


async def create_dish(db: AsyncSession, data: DishCreate) -> Dish:
    stall = await db.get(Stall, data.stall_id)
    if not stall:
        raise BizError(ErrorCode.NOT_FOUND, "摊位不存在")
    d = Dish(stall_id=data.stall_id, name=data.name, price=data.price, image=data.image)
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


async def update_dish(db: AsyncSession, dish_id: str, data: DishCreate) -> Dish:
    d = await get_dish(db, dish_id)
    d.name = data.name
    d.price = data.price
    d.image = data.image
    await db.commit()
    await db.refresh(d)
    return d


async def delete_dish(db: AsyncSession, dish_id: str) -> None:
    d = await get_dish(db, dish_id)
    await db.delete(d)
    await db.commit()


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

"""食堂业务逻辑。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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


async def list_canteens(
    db: AsyncSession,
    *,
    campus: str = "",
    zone: str = "",
    canteen_type: str = "",
    semester: str = "",
    keyword: str = "",
) -> list:
    # N+1 修复：CanteenOut 嵌套 stalls->dishes，一次性 selectinload 加载，避免逐层再查。
    # P2-17：评价不再随载——Dish.reviews 已从模型级 selectin 改回默认惰性，
    # 列表响应不序列化评价，无需也无法触发其加载（评价只经 list_reviews 按需查）。
    stmt = select(Canteen).options(selectinload(Canteen.stalls).selectinload(Stall.dishes))
    if campus:
        stmt = stmt.where(Canteen.campus == campus)
    if zone:
        stmt = stmt.where(Canteen.zone == zone)
    if canteen_type:
        stmt = stmt.where(Canteen.canteen_type == canteen_type)
    if semester:
        # 学期为空表示"长期开放"，应与指定学期同时存在（OR 语义）
        stmt = stmt.where((Canteen.semester == semester) | (Canteen.semester == ""))
    if keyword:
        stmt = stmt.where(Canteen.name.ilike(f"%{keyword}%"))
    rows = (await db.scalars(stmt.order_by(Canteen.created_at.desc()))).all()
    return [CanteenOut.model_validate(c).model_dump() for c in rows]


async def create_canteen(db: AsyncSession, data: CanteenCreate) -> Canteen:
    c = Canteen(**data.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def get_canteen(db: AsyncSession, canteen_id: str) -> Canteen:
    # N+1 修复：详情序列化含 stalls->dishes，预加载避免逐层查询（评价不随载，见 list_canteens）
    stmt = (
        select(Canteen)
        .where(Canteen.id == canteen_id)
        .options(selectinload(Canteen.stalls).selectinload(Stall.dishes))
    )
    c = (await db.scalars(stmt)).first()
    if not c:
        raise BizError(ErrorCode.NOT_FOUND, "食堂不存在")
    return c


async def update_canteen(db: AsyncSession, canteen_id: str, data: CanteenCreate) -> Canteen:
    c = await get_canteen(db, canteen_id)
    payload = data.model_dump()
    for field, value in payload.items():
        setattr(c, field, value)
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
    # 同一用户对同一菜品仅允许一条评价：接口可被脚本反复调用，无限制时
    # 一条菜品的评价列表会被单用户刷屏（重复提交转 409）
    dup = await db.scalar(
        select(CanteenReview).where(
            CanteenReview.dish_id == str(dish.id), CanteenReview.user_id == str(user.id)
        )
    )
    if dup:
        raise BizError(ErrorCode.CONFLICT, "您已评价过该菜品")
    r = CanteenReview(
        dish_id=str(dish.id), user_id=str(user.id),
        rating=data.rating, content=data.content,
    )
    db.add(r)
    try:
        await db.commit()
    except IntegrityError as exc:
        # P1-7：并发双插由 uq_canteen_review_user 唯一索引兜底，转 409。
        await db.rollback()
        raise BizError(ErrorCode.CONFLICT, "您已评价过该菜品") from exc
    await db.refresh(r)
    return r


async def list_reviews(db: AsyncSession, dish_id: str) -> list:
    rows = (await db.scalars(
        select(CanteenReview).where(CanteenReview.dish_id == dish_id).order_by(CanteenReview.created_at.desc())
    )).all()
    return [CanteenReviewOut.model_validate(r).model_dump() for r in rows]

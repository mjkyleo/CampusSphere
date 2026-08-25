"""课程业务逻辑。"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizError, ErrorCode
from app.modules.auth.models import User
from app.modules.course.models import Course, CourseReview
from app.modules.course.schemas import (
    CourseCreate,
    CourseOut,
    CourseReviewCreate,
    CourseReviewOut,
)


async def list_courses(db: AsyncSession, keyword: str = "", page: int = 1, page_size: int = 20) -> dict:
    stmt = select(Course)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(Course.name.ilike(like) | Course.code.ilike(like))
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await db.scalars(stmt.order_by(Course.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return {
        "items": [CourseOut.model_validate(c).model_dump() for c in rows],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


async def create_course(db: AsyncSession, data: CourseCreate) -> Course:
    dup = await db.scalar(select(Course).where(Course.code == data.code))
    if dup:
        raise BizError(ErrorCode.CONFLICT, "课程代码已存在")
    course = Course(**data.model_dump())
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


async def get_course(db: AsyncSession, course_id: str) -> Course:
    course = await db.get(Course, course_id)
    if not course:
        raise BizError(ErrorCode.NOT_FOUND, "课程不存在")
    return course


async def add_review(db: AsyncSession, course: Course, user: User, data: CourseReviewCreate) -> CourseReview:
    review = CourseReview(
        course_id=str(course.id), user_id=str(user.id),
        rating=data.rating, content=data.content,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


async def list_reviews(db: AsyncSession, course_id: str) -> list:
    rows = (await db.scalars(
        select(CourseReview).where(CourseReview.course_id == course_id).order_by(CourseReview.created_at.desc())
    )).all()
    return [CourseReviewOut.model_validate(r).model_dump() for r in rows]

"""课程路由：/api/courses/*。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BizError, ErrorCode
from app.core.response import ApiResponse
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.course.schemas import CourseCreate, CourseReviewCreate, CourseOut, CourseReviewOut
from app.modules.course.service import (
    add_review,
    create_course,
    get_course,
    list_courses,
    list_reviews,
)

router = APIRouter(prefix="/api/courses", tags=["course"])


@router.get("", response_model=ApiResponse[dict])
async def list_all(
    keyword: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return ApiResponse.ok(data=await list_courses(db, keyword=keyword, page=page, page_size=page_size))


@router.post("", response_model=ApiResponse[CourseOut])
async def create(
    data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    course = await create_course(db, data)
    return ApiResponse.ok(data=CourseOut.model_validate(course))


@router.get("/{course_id}", response_model=ApiResponse[dict])
async def detail(course_id: str, db: AsyncSession = Depends(get_db)):
    course = await get_course(db, course_id)
    reviews = await list_reviews(db, str(course.id))
    return ApiResponse.ok(data={"course": CourseOut.model_validate(course).model_dump(), "reviews": reviews})


@router.post("/{course_id}/reviews", response_model=ApiResponse[CourseReviewOut])
async def review(
    course_id: str,
    data: CourseReviewCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    course = await get_course(db, course_id)
    r = await add_review(db, course, user, data)
    return ApiResponse.ok(data=CourseReviewOut.model_validate(r))

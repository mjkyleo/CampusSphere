"""课程业务逻辑。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
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


async def list_courses(
    db: AsyncSession, keyword: str = "", department: str = "", page: int = 1, page_size: int = 20
) -> dict:
    # P2-17：Course.reviews 已从模型级 selectin 改回默认惰性——列表不再把
    # 全库课程评价拉进内存（响应不序列化它们），评价经 list_reviews 按需查。
    stmt = select(Course)
    if keyword:
        from app.common.utils import escape_like

        like = f"%{escape_like(keyword)}%"
        stmt = stmt.where(Course.name.ilike(like, escape="\\") | Course.code.ilike(like, escape="\\"))
    if department:
        stmt = stmt.where(Course.department == department)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await db.scalars(stmt.order_by(Course.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return {
        "items": [CourseOut.model_validate(c).model_dump() for c in rows],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


async def create_course(db: AsyncSession, data: CourseCreate) -> Course:
    # 院系收敛到后台配置列表内（同 job/share/teammate 的分类收敛模式）：
    # 前端传了已被运营下线的院系时落到"其他"，避免筛选项与数据脱节。
    from app.modules.admin.service import get_course_departments

    payload = data.model_dump()
    if payload.get("department"):
        departments = await get_course_departments(db)
        if payload["department"] not in departments:
            # 不在配置列表内：落空串（与模型默认一致，等价"未分组"），
            # 避免写进一个筛选页点不出来的脏院系
            payload["department"] = ""
    course = Course(**payload)
    db.add(course)
    try:
        await db.commit()
    except IntegrityError as exc:
        # P3：并发创建同 code 课程——唯一约束兜底，转 409 而非裸 500
        await db.rollback()
        raise BizError(ErrorCode.CONFLICT, "课程代码已存在") from exc
    await db.refresh(course)
    return course


async def get_course(db: AsyncSession, course_id: str) -> Course:
    course = await db.get(Course, course_id)
    if not course:
        raise BizError(ErrorCode.NOT_FOUND, "课程不存在")
    return course


async def add_review(db: AsyncSession, course: Course, user: User, data: CourseReviewCreate) -> CourseReview:
    # 同一用户对同一课程仅允许一条评价（与食堂评价同规则，防脚本刷评）
    dup = await db.scalar(
        select(CourseReview).where(
            CourseReview.course_id == str(course.id), CourseReview.user_id == str(user.id)
        )
    )
    if dup:
        raise BizError(ErrorCode.CONFLICT, "您已评价过该课程")
    review = CourseReview(
        course_id=str(course.id), user_id=str(user.id),
        rating=data.rating, content=data.content,
    )
    db.add(review)
    try:
        await db.commit()
    except IntegrityError as exc:
        # P1-7：并发双击/脚本同时插入时 SELECT 拦不住，由
        # uq_course_review_user 唯一索引兜底，此处转 409。
        await db.rollback()
        raise BizError(ErrorCode.CONFLICT, "您已评价过该课程") from exc
    await db.refresh(review)
    return review


async def list_reviews(db: AsyncSession, course_id: str) -> list:
    rows = (await db.scalars(
        select(CourseReview).where(CourseReview.course_id == course_id).order_by(CourseReview.created_at.desc())
    )).all()
    return [CourseReviewOut.model_validate(r).model_dump() for r in rows]

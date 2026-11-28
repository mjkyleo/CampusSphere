"""兼职业务逻辑。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import app.tasks.notify as notify_tasks
from app.common.enums import ApplicationStatus, JobStatus
from app.common.utils import escape_like
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.modules.ai.service import check_content_safety
from app.modules.auth.models import User
from app.modules.job.models import Job, JobApplication
from app.modules.job.schemas import (
    JobApplicationCreate,
    JobApplicationOut,
    JobCreate,
    JobOut,
)

_logger = get_logger("job.service")


async def list_jobs(
    db: AsyncSession,
    keyword: str = "",
    category: str = "",
    status: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = select(Job)
    if keyword:
        # P3：转义 LIKE 通配符，防止 "%" / "_" 被当作模式匹配（ILIKE 通配符转义助手）
        like = f"%{escape_like(keyword)}%"
        stmt = stmt.where(Job.title.ilike(like, escape="\\"))
    if category:
        stmt = stmt.where(Job.category == category)
    if status is not None:
        stmt = stmt.where(Job.status == status)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await db.scalars(stmt.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return {
        "items": [JobOut.model_validate(j).model_dump() for j in rows],
        "total": total or 0, "page": page, "page_size": page_size,
    }


async def create_job(db: AsyncSession, poster: User, data: JobCreate) -> Job:
    # 分类收敛到后台配置列表内（运营下线某个分类后，旧客户端传来的值不至于
    # 变成筛选页里点不动的僵尸分类）
    from app.modules.admin.service import normalize_category

    payload = data.model_dump()
    salary_cents = payload.pop("salary_cents", None)
    if salary_cents is not None:
        payload["salary"] = salary_cents
    payload["category"] = await normalize_category(db, "job", payload.get("category", ""))

    # 内容预审：命中敏感词时拒绝发布（默认关闭，可在后台开启）
    moderation_text = "\n".join(
        str(payload.get(k, ""))
        for k in ("title", "description", "company", "location", "contact", "requirements")
    ).strip()
    moderation = await check_content_safety(db, moderation_text)
    if not moderation["safe"]:
        raise BizError(ErrorCode.FORBIDDEN, "发布内容涉嫌违规，请修改后重试")

    job = Job(poster_id=str(poster.id), **payload)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: str) -> Job:
    job = await db.get(Job, job_id)
    if not job:
        raise BizError(ErrorCode.NOT_FOUND, "岗位不存在")
    return job


async def apply_job(db: AsyncSession, job: Job, applicant: User, data: JobApplicationCreate) -> JobApplication:
    if job.status != JobStatus.OPEN.value:
        raise BizError(ErrorCode.CONFLICT, "岗位已关闭")
    existing = await db.scalar(
        select(JobApplication).where(
            JobApplication.job_id == str(job.id), JobApplication.applicant_id == str(applicant.id)
        )
    )
    if existing:
        raise BizError(ErrorCode.CONFLICT, "已申请过该岗位")
    app = JobApplication(
        job_id=str(job.id), applicant_id=str(applicant.id),
        status=ApplicationStatus.PENDING.value, note=data.note,
    )
    db.add(app)
    try:
        await db.commit()
    except IntegrityError as exc:
        # P2-3：并发双插由 uq_job_application 唯一索引兜底，转 409。
        await db.rollback()
        raise BizError(ErrorCode.CONFLICT, "已申请过该岗位") from exc
    await db.refresh(app)
    try:
        notify_tasks.send_notify.delay(
            str(job.poster_id),
            f"{applicant.nickname or applicant.username} 申请了兼职：{job.title}",
            "请尽快在「兼职广场」中查看申请详情。",
            channel="inapp",
        )
    except Exception as exc:
        _logger.warning("notify_dispatch_failed", job_id=str(job.id), error=str(exc))
    return app


async def list_applications(db: AsyncSession, job_id: str, poster_id: str) -> list:
    job = await db.get(Job, job_id)
    if not job or str(job.poster_id) != poster_id:
        raise BizError(ErrorCode.FORBIDDEN, "无权查看")
    rows = (await db.scalars(
        select(JobApplication).where(JobApplication.job_id == job_id)
    )).all()
    return [JobApplicationOut.model_validate(a).model_dump() for a in rows]

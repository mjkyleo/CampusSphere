"""兼职业务逻辑。"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ApplicationStatus, JobStatus
from app.core.exceptions import BizError, ErrorCode
from app.modules.auth.models import User
from app.modules.job.models import Job, JobApplication
from app.modules.job.schemas import (
    JobApplicationCreate,
    JobApplicationOut,
    JobCreate,
    JobOut,
)


async def list_jobs(db: AsyncSession, keyword: str = "", status: int | None = None, page: int = 1, page_size: int = 20) -> dict:
    stmt = select(Job)
    if keyword:
        stmt = stmt.where(Job.title.ilike(f"%{keyword}%"))
    if status is not None:
        stmt = stmt.where(Job.status == status)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await db.scalars(stmt.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return {
        "items": [JobOut.model_validate(j).model_dump() for j in rows],
        "total": total or 0, "page": page, "page_size": page_size,
    }


async def create_job(db: AsyncSession, poster: User, data: JobCreate) -> Job:
    job = Job(poster_id=str(poster.id), **data.model_dump())
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
    await db.commit()
    await db.refresh(app)
    return app


async def list_applications(db: AsyncSession, job_id: str, poster_id: str) -> list:
    job = await db.get(Job, job_id)
    if not job or str(job.poster_id) != poster_id:
        raise BizError(ErrorCode.FORBIDDEN, "无权查看")
    rows = (await db.scalars(
        select(JobApplication).where(JobApplication.job_id == job_id)
    )).all()
    return [JobApplicationOut.model_validate(a).model_dump() for a in rows]

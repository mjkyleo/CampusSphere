"""兼职路由：/api/jobs/*。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.job.schemas import (
    JobApplicationCreate,
    JobApplicationOut,
    JobCreate,
    JobOut,
)
from app.modules.job.service import (
    apply_job,
    create_job,
    get_job,
    list_applications,
    list_jobs,
)

router = APIRouter(prefix="/api/jobs", tags=["job"])


@router.get("", response_model=ApiResponse[dict])
async def list_all(
    keyword: str = Query(default=""),
    status: int = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ApiResponse.ok(data=await list_jobs(
        db, keyword=keyword, status=status if status is not None else None,
        page=page, page_size=page_size,
    ))


@router.post("", response_model=ApiResponse[JobOut])
async def create(data: JobCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return ApiResponse.ok(data=JobOut.model_validate(await create_job(db, user, data)))


@router.post("/{job_id}/apply", response_model=ApiResponse[JobApplicationOut])
async def apply(job_id: str, data: JobApplicationCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    job = await get_job(db, job_id)
    return ApiResponse.ok(data=JobApplicationOut.model_validate(await apply_job(db, job, user, data)))


@router.get("/{job_id}/applications", response_model=ApiResponse[list])
async def applications(job_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return ApiResponse.ok(data=await list_applications(db, job_id, str(user.id)))

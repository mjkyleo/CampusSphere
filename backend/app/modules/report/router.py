"""举报路由：/api/reports/*。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.report.schemas import ReportCreate, ReportHandle, ReportOut
from app.modules.report.service import (
    check_auto_ban,
    handle_report,
    list_reports,
    submit_report,
)

router = APIRouter(prefix="/api/reports", tags=["report"])


@router.post("", response_model=ApiResponse[ReportOut])
async def submit(data: ReportCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    # 提交后自动评估封禁
    report = await submit_report(db, user, data)
    if data.target_type == "user":
        await check_auto_ban(db, data.target_id)
    return ApiResponse.ok(data=ReportOut.model_validate(report))


@router.get("", response_model=ApiResponse[dict])
async def list_all(
    status: int = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ApiResponse.ok(data=await list_reports(
        db, status=status if status is not None else None, page=page, page_size=page_size
    ))


@router.post("/{report_id}/handle", response_model=ApiResponse[ReportOut])
async def handle(report_id: str, data: ReportHandle, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    report = await handle_report(db, report_id, user, data)
    return ApiResponse.ok(data=ReportOut.model_validate(report))

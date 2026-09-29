"""举报业务逻辑 + 自动封禁规则。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ReportStatus, UserStatus
from app.core.config import settings
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.report.models import Report, ReportLog
from app.modules.report.schemas import ReportOut

_logger = get_logger("report.service")


async def submit_report(db: AsyncSession, reporter: User, data) -> Report:
    report = Report(
        reporter_id=str(reporter.id),
        target_type=data.target_type,
        target_id=str(data.target_id),
        reason=data.reason,
        status=ReportStatus.PENDING.value,
    )
    db.add(report)
    try:
        await db.commit()
    except IntegrityError as exc:
        # P1-9：同一举报人对同一目标只允许一条工单，并发双击由
        # uq_report_reporter_target 唯一索引兜底，转 409。
        await db.rollback()
        raise BizError(ErrorCode.CONFLICT, "请勿重复提交相同举报") from exc
    await db.refresh(report)
    _logger.info("report_submitted", report=str(report.id))
    return report


async def list_reports(db: AsyncSession, status: int | None = None, page: int = 1, page_size: int = 20) -> dict:
    stmt = select(Report)
    if status is not None:
        stmt = stmt.where(Report.status == status)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await db.scalars(stmt.order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return {
        "items": [ReportOut.model_validate(r).model_dump() for r in rows],
        "total": total or 0, "page": page, "page_size": page_size,
    }


async def handle_report(db: AsyncSession, report_id: str, operator: User, data) -> Report:
    report = await db.get(Report, report_id)
    if not report:
        raise BizError(ErrorCode.NOT_FOUND, "工单不存在")
    log = ReportLog(
        report_id=str(report.id), operator_id=str(operator.id),
        action=data.action, note=data.note,
    )
    db.add(log)

    if data.action == "ban" and report.target_type == "user":
        await _ban_user(db, report.target_id, reason=f"举报封禁: {report.id}")
        report.status = ReportStatus.RESOLVED.value
    elif data.action == "resolve":
        report.status = ReportStatus.RESOLVED.value
    elif data.action == "reject":
        report.status = ReportStatus.REJECTED.value
    report.handled_by = str(operator.id)
    await db.commit()
    await db.refresh(report)
    return report


async def _ban_user(db: AsyncSession, user_id: str, reason: str = "") -> None:
    user = await db.get(User, user_id)
    if not user:
        return
    user.status = UserStatus.BANNED.value
    await db.commit()
    _logger.warning("user_banned", user_id=user_id, reason=reason)


async def check_auto_ban(db: AsyncSession, target_user_id: str) -> bool:
    """自动封禁规则：**不同举报人**的有效举报达到阈值则封禁。

    P1-9 修复统计口径：
    - 只统计 PENDING / RESOLVED——管理员驳回（REJECTED）的举报不再永久计入，
      否则历史驳回会让目标"永不超标"，管理员驳回形同虚设；
    - 按 distinct 举报人计数——同一人重复提交（接口层已去重，防御历史脏数据
      或索引缺失的老库）不再一人顶 N 票，5 个小号即可封人的滥用路径被堵死。
    """
    threshold = int((settings.report_policy or {}).get("auto_ban_threshold", 5))
    count = await db.scalar(
        select(func.count(func.distinct(Report.reporter_id)))
        .select_from(Report)
        .where(
            Report.target_type == "user",
            Report.target_id == target_user_id,
            Report.status.in_([ReportStatus.PENDING.value, ReportStatus.RESOLVED.value]),
        )
    )
    if (count or 0) >= threshold:
        await _ban_user(db, target_user_id, reason=f"自动封禁（{count} 名不同用户举报）")
        return True
    return False

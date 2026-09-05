"""审计日志服务：统一记录入口与后台查询。

设计要点
--------
``record_audit_log`` 是**旁路**调用：审计是辅助能力，它的失败绝不能
影响用户的正常操作（不能因为写不了日志就注册失败）。因此内部吞掉所有异常，
但会打 error 日志 —— 否则会静默丢失全部留痕而不自知。

它使用**独立的数据库会话**提交，这一点很关键：业务失败（登录失败、
注册被拒）恰恰是最需要留痕的事件，而失败往往伴随事务回滚，
若与业务共用会话，这些日志会随回滚一起消失。
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.modules.audit.actions import ActorType, AuditResult
from app.modules.audit.models import AuditLog

_logger = get_logger("audit.service")

_UA_MAX = 512


def _client_ip(request: Request) -> str:
    """取客户端 IP：优先 X-Forwarded-For（nginx 反代场景），回退直连地址。"""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        # 反代链路上形如 "client, proxy1, proxy2"，第一个才是真实来源
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


async def record_audit_log(
    *,
    action: str,
    actor_type: str = ActorType.ANONYMOUS,
    actor_id: str | None = None,
    actor_label: str = "",
    result: str = AuditResult.SUCCESS,
    target_type: str = "",
    target_id: str | None = None,
    detail: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    """记录一条审计日志。任何异常都被吞掉，绝不向调用方抛出。"""
    ip = ""
    user_agent = ""
    request_id = ""
    if request is not None:
        ip = _client_ip(request)[:64]
        user_agent = request.headers.get("user-agent", "")[:_UA_MAX]
        request_id = str(getattr(request.state, "request_id", "") or "")[:64]

    entry = AuditLog(
        action=action,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_label=(actor_label or "")[:128],
        result=result,
        target_type=target_type,
        target_id=target_id,
        detail=detail or {},
        ip=ip,
        user_agent=user_agent,
        request_id=request_id,
    )

    try:
        async with SessionLocal() as session:
            session.add(entry)
            await session.commit()
    except Exception as exc:  # 审计失败不影响业务，但必须留下痕迹
        _logger.error("audit_log_write_failed", action=action, error=str(exc))


async def list_audit_logs(
    db: AsyncSession,
    *,
    action: str | None = None,
    actor_id: str | None = None,
    actor_type: str | None = None,
    result: str | None = None,
    keyword: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    """分页查询审计日志，返回 ``(数据, 总数)``。"""
    conditions = []
    if action:
        conditions.append(AuditLog.action == action)
    if actor_id:
        conditions.append(AuditLog.actor_id == actor_id)
    if actor_type:
        conditions.append(AuditLog.actor_type == actor_type)
    if result:
        conditions.append(AuditLog.result == result)
    if keyword:
        like = f"%{keyword}%"
        conditions.append(
            or_(
                AuditLog.actor_label.ilike(like),
                AuditLog.action.ilike(like),
                AuditLog.ip.ilike(like),
            )
        )

    stmt = select(AuditLog)
    if conditions:
        stmt = stmt.where(*conditions)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = await db.scalars(
        stmt.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
    )
    return list(rows.all()), int(total or 0)

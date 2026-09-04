"""审计日志管理接口（仅管理员可见）。

路由挂在 ``/api/admin`` 下，与 admin 模块同前缀 —— 它们是同一类"后台能力"，
拆到独立文件只是为了避免 admin/router.py 继续膨胀。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_scope
from app.core.response import ApiResponse
from app.modules.audit.actions import (
    ACTION_LABELS,
    ACTOR_LABELS,
    RESULT_LABELS,
)
from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditActionOption, AuditLogOut, AuditLogPage
from app.modules.audit.service import list_audit_logs

router = APIRouter(prefix="/api/admin", tags=["audit"])

# 单次返回上限：审计表增长很快，不封顶一次查询可能拖垮接口
_MAX_LIMIT = 200


def _to_out(row: AuditLog) -> AuditLogOut:
    """ORM → DTO，顺带把动作/结果翻译成中文展示。"""
    return AuditLogOut(
        id=row.id,
        created_at=row.created_at,
        actor_type=row.actor_type,
        actor_id=row.actor_id,
        actor_label=row.actor_label,
        action=row.action,
        result=row.result,
        target_type=row.target_type,
        target_id=row.target_id,
        detail=row.detail or {},
        ip=row.ip,
        user_agent=row.user_agent,
        request_id=row.request_id,
        action_label=ACTION_LABELS.get(row.action, row.action),
        result_label=RESULT_LABELS.get(row.result, row.result),
        actor_type_label=ACTOR_LABELS.get(row.actor_type, row.actor_type),
    )


@router.get("/audit-logs", response_model=ApiResponse[AuditLogPage])
async def get_audit_logs(
    action: str | None = Query(default=None, description="按动作过滤"),
    actor_id: str | None = Query(default=None, description="按操作者 ID 过滤"),
    actor_type: str | None = Query(default=None, description="user/admin/system/anonymous"),
    result: str | None = Query(default=None, description="success/failure"),
    keyword: str | None = Query(default=None, description="按账号/IP/动作模糊搜索"),
    limit: int = Query(default=50, ge=1, le=_MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_scope("audit")),
):
    """分页查询审计日志，按时间倒序。"""
    rows, total = await list_audit_logs(
        db,
        action=action,
        actor_id=actor_id,
        actor_type=actor_type,
        result=result,
        keyword=keyword,
        limit=limit,
        offset=offset,
    )
    return ApiResponse.ok(
        data=AuditLogPage(
            items=[_to_out(r) for r in rows],
            total=total,
            limit=limit,
            offset=offset,
        )
    )


@router.get("/audit-logs/actions", response_model=ApiResponse[list[AuditActionOption]])
async def get_audit_actions(_=Depends(require_scope("audit"))):
    """动作字典，供后台筛选下拉框使用（避免前端硬编码一份）。"""
    return ApiResponse.ok(
        data=[AuditActionOption(value=k, label=v) for k, v in ACTION_LABELS.items()]
    )

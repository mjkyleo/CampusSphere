"""管理员鉴权依赖（供 admin 模块与其他管理端路由共用）。"""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BizError, ErrorCode
from app.modules.admin.gateway import require_admin_gateway
from app.modules.admin.models import AdminUser
from app.modules.admin.service import get_admin


async def get_current_admin(request: Request, db: AsyncSession = Depends(get_db)) -> AdminUser:
    admin_id = getattr(request.state, "user_id", None)
    if not admin_id:
        raise BizError(ErrorCode.UNAUTHORIZED, "管理员未认证")
    admin = await get_admin(db, admin_id)
    if admin.disabled:
        raise BizError(ErrorCode.FORBIDDEN, "账号已禁用")
    return admin


async def require_admin(
    request: Request,
    _gw: None = Depends(require_admin_gateway),
    admin: AdminUser = Depends(get_current_admin),
) -> AdminUser:
    """组合依赖：先校验网关令牌（缺失则 404 屏蔽端点），再校验管理员身份。"""
    return admin

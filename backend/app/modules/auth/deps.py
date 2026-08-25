"""认证依赖：从请求上下文解析当前用户（由网关中间件写入 request.state.user_id）。"""

from __future__ import annotations

import uuid

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BizError, ErrorCode
from app.modules.auth.models import User


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    """解析当前登录用户；未认证抛出 401。"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise BizError(ErrorCode.UNAUTHORIZED, "未认证或登录已过期")
    user = await db.get(User, user_id)
    if not user:
        raise BizError(ErrorCode.NOT_FOUND, "用户不存在")
    if user.status == 1:  # BANNED
        raise BizError(ErrorCode.FORBIDDEN, "账号已被封禁")
    return user

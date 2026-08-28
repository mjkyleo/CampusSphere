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


async def get_current_user_optional(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User | None:
    """解析当前登录用户；未登录时返回 None（用于公开读取接口）。"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return None
    user = await db.get(User, user_id)
    if not user:
        return None
    if user.status == 1:  # BANNED
        return None
    return user


def require_owner(owner_id: str | uuid.UUID, current_user: User) -> None:
    """资源归属校验（IDOR 防护）。

    当前用户不是资源拥有者时抛 403。在各模块的写/删/越权读取接口统一调用，
    替代散落在各 router 中的 ``if str(x.owner_id) != str(user.id): raise`` 样板，
    保证「越权访问」语义一致、可被测试守护。

    :param owner_id: 资源记录的归属用户 ID（字符串或 UUID 均可）。
    :param current_user: 经 ``get_current_user`` 解析出的当前用户。
    """
    if str(owner_id) != str(current_user.id):
        raise BizError(ErrorCode.FORBIDDEN, "无权操作该资源")

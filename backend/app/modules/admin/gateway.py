"""管理员后台网关：HMAC 短时令牌，用于隐藏 /api/admin/* 的可达性。

设计要点：
- 仅 ``POST /api/admin/discover`` 公开：客户端用配置好的网关密钥（gateway_key）换取一个
  由 ``HMAC-SHA256(gateway_key + SECRET_KEY + 时间槽)`` 派生的短时令牌（默认 1 小时轮换）。
- 其余所有 ``/api/admin/*`` 必须在请求头携带 ``X-Admin-Gateway: <token>``，否则一律返回 404，
  让未授权者看起来像接口不存在（避免探测与信息泄露）。
- 令牌为无状态派生，无需落库；校验时允许当前时间槽与前一个时间槽（轮换宽限）。
- 本地开发（DEBUG=true 或 admin_gateway_enforce=false）放宽：网关校验直通，便于联调。
"""

from __future__ import annotations

import hashlib
import hmac
import time

from fastapi import Header, HTTPException, Request

from app.core.config import settings

GATEWAY_HEADER = "X-Admin-Gateway"


def gateway_enforced() -> bool:
    """是否强制要求网关令牌（生产默认开启，本地开发放宽）。"""
    return settings.admin_gateway_enforce and not settings.debug


def _derive_secret() -> str:
    # 组合 gateway_key + secret_key，避免明文回显，也防止 gateway_key 过短被直接猜解
    return f"{settings.admin_gateway_key}|{settings.secret_key}"


def _current_slot(rotate_seconds: int) -> int:
    return int(time.time()) // max(rotate_seconds, 1)


def _sign(slot: int) -> str:
    msg = f"admin-gateway:{slot}".encode()
    return hmac.new(_derive_secret().encode("utf-8"), msg, hashlib.sha256).hexdigest()


def issue_gateway_token() -> str:
    """签发当前时间槽的网关令牌（无状态，无需 DB）。"""
    return _sign(_current_slot(settings.admin_gateway_rotate_seconds))


def verify_gateway_token(token: str | None) -> bool:
    """校验网关令牌：本地放宽时直通；否则要求与当前/前一时间槽签名一致。"""
    if not gateway_enforced():
        return True
    if not token or not settings.admin_gateway_key:
        return False
    slot = _current_slot(settings.admin_gateway_rotate_seconds)
    # 允许当前槽与前一槽，覆盖轮换瞬间的时间偏差
    return hmac.compare_digest(token, _sign(slot)) or hmac.compare_digest(token, _sign(slot - 1))


async def require_admin_gateway(
    request: Request,
    x_admin_gateway: str | None = Header(default=None, alias=GATEWAY_HEADER),
) -> None:
    """依赖：未携带有效网关令牌时一律 404，让端点对外"不存在"。"""
    if not verify_gateway_token(x_admin_gateway):
        # 故意返回 404 而非 401/403，避免暴露管理端存在
        raise HTTPException(status_code=404, detail="Not Found")

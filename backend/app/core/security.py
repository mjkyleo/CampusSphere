"""安全工具：密码哈希、JWT 签发/校验、jti 黑名单。

- access token 15m，refresh token 7d
- 注销时把 refresh/access 的 jti 写入 Redis 黑名单（SET + TTL 剩余有效期）
- 网关中间件读取 Redis 校验黑名单
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import redis_get, redis_set

_logger = get_logger("core.security")

# ---------- 密码 ----------
def hash_password(password: str) -> str:
    """bcrypt 哈希。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """校验明文密码与哈希。"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False

# ---------- JWT ----------
def _now() -> datetime:
    return datetime.now(UTC)


def _create_token(
    user_id: str, token_type: str, expires_delta: timedelta, jti: str | None = None
) -> str:
    jti = jti or uuid.uuid4().hex
    now = _now()
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str, jti: str | None = None) -> str:
    return _create_token(
        user_id,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
        jti,
    )


def create_refresh_token(user_id: str, jti: str | None = None) -> str:
    return _create_token(
        user_id,
        "refresh",
        timedelta(days=settings.refresh_token_expire_days),
        jti,
    )


def decode_token(token: str) -> dict:
    """验签 + 过期检查，返回 payload。"""
    return jwt.decode(
        token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )


def get_token_jti(token: str) -> str | None:
    try:
        return decode_token(token).get("jti")
    except jwt.PyJWTError:
        return None

# ---------- 黑名单 ----------
_BLACKLIST_PREFIX = "jwt:blacklist:"


async def revoke_token(token: str) -> None:
    """注销：把 jti 加入黑名单，TTL 为 token 剩余有效期。"""
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return
    jti = payload.get("jti")
    if not jti:
        return
    exp = payload.get("exp")
    ttl = None
    if exp:
        ttl = max(int(exp - _now().timestamp()), 1)
    await redis_set(f"{_BLACKLIST_PREFIX}{jti}", "1", ttl)


async def is_token_revoked(token: str) -> bool:
    """校验 token 是否在黑名单。"""
    jti = get_token_jti(token)
    if not jti:
        return True
    val = await redis_get(f"{_BLACKLIST_PREFIX}{jti}")
    return val is not None

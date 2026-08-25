"""认证模块业务逻辑：注册/登录/刷新/注销/验证码/邮箱验证。"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import re

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserStatus
from app.common.utils import generate_code, is_valid_email, is_valid_phone
from app.core.config import settings
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.core.redis import redis_get, redis_incr, redis_set
from app.core.security import (
    _create_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_jti,
    revoke_token,
)
from app.modules.auth.models import OAuthAccount, RefreshToken, User

_logger = get_logger("auth.service")

_CODE_TTL = 300  # 验证码 5 分钟有效
_RATE_LIMIT_PREFIX = "vcode:limit:"


async def register(db: AsyncSession, data) -> User:
    """注册新用户（用户名唯一）。"""
    existing = await db.scalar(select(User).where(User.username == data.username))
    if existing:
        raise BizError(ErrorCode.CONFLICT, "用户名已存在")
    user = User(username=data.username, nickname=data.nickname or data.username)
    if data.email:
        if not is_valid_email(data.email):
            raise BizError(ErrorCode.VALIDATION, "邮箱格式不正确")
        dup = await db.scalar(select(User).where(User.email == data.email))
        if dup:
            raise BizError(ErrorCode.CONFLICT, "邮箱已被注册")
        user.email = data.email
    if data.phone:
        if not is_valid_phone(data.phone):
            raise BizError(ErrorCode.VALIDATION, "手机号格式不正确")
        dup = await db.scalar(select(User).where(User.phone == data.phone))
        if dup:
            raise BizError(ErrorCode.CONFLICT, "手机号已被注册")
        user.phone = data.phone
    user.status = UserStatus.NORMAL.value
    user.set_password(data.password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    _logger.info("user_registered", user_id=str(user.id))
    return user


async def authenticate(db: AsyncSession, account: str, password: str) -> Optional[User]:
    """统一账号校验：支持 自定义账号 / 邮箱 / 手机号 + 密码。"""
    account = (account or "").strip()
    if not account:
        return None
    user = await db.scalar(
        select(User).where(
            or_(
                User.username == account,
                User.phone == account,
                func.lower(User.email) == account.lower(),
            )
        )
    )
    if not user or not user.check_password(password):
        return None
    return user


async def _store_refresh(db: AsyncSession, user_id: uuid.UUID, jti: str) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    rt = RefreshToken(
        user_id=user_id, jti=jti, expires_at=expires_at, revoked=False
    )
    db.add(rt)
    await db.commit()


async def issue_tokens(db: AsyncSession, user: User) -> dict:
    """签发 access + refresh 并记录 refresh jti。"""
    access_jti = uuid.uuid4().hex
    refresh_jti = uuid.uuid4().hex
    access = create_access_token(str(user.id), access_jti)
    refresh = create_refresh_token(str(user.id), refresh_jti)
    await _store_refresh(db, user.id, refresh_jti)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
    }


async def login(db: AsyncSession, account: str, password: str) -> dict:
    """统一登录：账号（邮箱 / 手机号 / 自定义账号）+ 密码。"""
    user = await authenticate(db, account, password)
    if not user:
        raise BizError(ErrorCode.UNAUTHORIZED, "账号或密码错误")
    if user.status == UserStatus.BANNED.value:
        raise BizError(ErrorCode.FORBIDDEN, "账号已被封禁")
    return await issue_tokens(db, user)


async def refresh_token(db: AsyncSession, refresh_token: str) -> dict:
    try:
        payload = decode_token(refresh_token)
    except Exception:  # noqa: BLE001
        raise BizError(ErrorCode.UNAUTHORIZED, "refresh token 无效")
    if payload.get("type") != "refresh":
        raise BizError(ErrorCode.UNAUTHORIZED, "令牌类型错误")
    jti = payload.get("jti")
    rt = await db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if not rt or rt.revoked:
        raise BizError(ErrorCode.UNAUTHORIZED, "refresh token 已失效")
    user = await db.get(User, payload["sub"])
    if not user:
        raise BizError(ErrorCode.UNAUTHORIZED, "用户不存在")
    # 吊销旧 refresh，签发新 token
    rt.revoked = True
    await db.commit()
    return await issue_tokens(db, user)


async def logout(db: AsyncSession, access_token: str, refresh_token: str) -> None:
    await revoke_token(access_token)
    await revoke_token(refresh_token)
    jti = get_token_jti(refresh_token)
    if jti:
        rt = await db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
        if rt:
            rt.revoked = True
            await db.commit()
    _logger.info("user_logged_out")


async def send_code(target: str, purpose: str, limit_per_minute: int = 1) -> str:
    """生成并存储验证码；对同一 target 做发送频率限制（默认每分钟 1 次）。"""
    is_phone = is_valid_phone(target)
    is_mail = is_valid_email(target)
    if not (is_phone or is_mail):
        raise BizError(ErrorCode.VALIDATION, "target 必须是手机号或邮箱")
    limit_key = f"{_RATE_LIMIT_PREFIX}{purpose}:{target}"
    count = await redis_incr(limit_key, ttl=60)
    if limit_per_minute and count > limit_per_minute:
        raise BizError(ErrorCode.TOO_MANY_REQUESTS, "发送过于频繁，请稍后再试")
    code = generate_code(6)
    # 验证码存 Redis（带 TTL）；无 Redis 时降级为内存（仅开发）
    await redis_set(f"vcode:{purpose}:{target}", code, ttl=_CODE_TTL)
    _logger.info("verification_code_sent", target=target, purpose=purpose)
    return code


async def verify_code(target: str, code: str, purpose: str) -> bool:
    stored = await redis_get(f"vcode:{purpose}:{target}")
    if not stored or stored != code:
        return False
    # 校验成功即失效
    await redis_set(f"vcode:{purpose}:{target}", "", ttl=1)
    return True


async def phone_login(db: AsyncSession, target: str, code: str) -> dict:
    if not await verify_code(target, code, "login"):
        raise BizError(ErrorCode.VALIDATION, "验证码错误或已过期")
    user = await db.scalar(
        select(User).where((User.phone == target) | (User.email == target))
    )
    if not user:
        # 自动注册（手机号/邮箱登录即注册）
        username = target.replace("@", "_").replace(".", "_")[:64]
        user = User(username=username, nickname=username, status=UserStatus.NORMAL.value)
        if is_valid_phone(target):
            user.phone = target
        else:
            user.email = target
        user.set_password(uuid.uuid4().hex)  # 随机密码，后续引导设置
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return await issue_tokens(db, user)


async def create_email_verify_token(user: User) -> str:
    return _create_token(
        str(user.id),
        "email_verify",
        timedelta(hours=24),
        jti=uuid.uuid4().hex,
    )


async def verify_email(db: AsyncSession, token: str) -> User:
    try:
        payload = decode_token(token)
    except Exception:  # noqa: BLE001
        raise BizError(ErrorCode.VALIDATION, "验证链接无效或已过期")
    if payload.get("type") != "email_verify":
        raise BizError(ErrorCode.VALIDATION, "令牌类型错误")
    user = await db.get(User, payload["sub"])
    if not user:
        raise BizError(ErrorCode.NOT_FOUND, "用户不存在")
    if user.email:
        user.status = UserStatus.NORMAL.value
        await db.commit()
    return user


def get_current_user_id(payload: dict) -> str:
    return payload["sub"]


# ---------------------------------------------------------------------------
# 邮箱注册规则（后台 /api/admin/auth/email-config 可动态覆盖）
# ---------------------------------------------------------------------------


async def get_email_register_rule(db: AsyncSession) -> dict:
    """读取邮箱注册规则：后台 DB 配置优先，school.yaml 兜底。"""
    from app.modules.admin.service import get_email_register_config

    return await get_email_register_config(db)


def validate_email_rule(email: str, rule: dict) -> None:
    """校验邮箱是否符合后台配置的注册/绑定规则，不通过抛 BizError。"""
    if not is_valid_email(email):
        raise BizError(ErrorCode.VALIDATION, "邮箱格式不正确")
    if not rule.get("enabled", True):
        raise BizError(ErrorCode.FORBIDDEN, "邮箱注册/绑定功能暂未开放")
    domains = [str(d).lower() for d in (rule.get("domains") or [])]
    if domains:
        domain = email.split("@", 1)[1].lower()
        if domain not in domains:
            raise BizError(
                ErrorCode.VALIDATION,
                f"仅支持 {', '.join(domains)} 域名的邮箱",
            )
    pattern = str(rule.get("pattern") or "")
    if pattern:
        try:
            ok = re.fullmatch(pattern, email) is not None
        except re.error:
            ok = True  # 后台配置了非法正则时放行，避免阻断正常流程
        if not ok:
            raise BizError(ErrorCode.VALIDATION, "邮箱不符合注册规则")


# ---------------------------------------------------------------------------
# 邮箱注册 / 统一登录 / 多方式绑定
# ---------------------------------------------------------------------------


async def register_by_email(db: AsyncSession, data) -> User:
    """邮箱验证码注册：校验邮箱规则 + 验证码 + 唯一性，自动生成用户名。"""
    email = (data.email or "").strip().lower()
    rule = await get_email_register_rule(db)
    validate_email_rule(email, rule)
    if not await verify_code(email, data.code, "register"):
        raise BizError(ErrorCode.VALIDATION, "邮箱验证码错误或已过期")
    dup = await db.scalar(select(User).where(func.lower(User.email) == email))
    if dup:
        raise BizError(ErrorCode.CONFLICT, "该邮箱已注册，请直接登录")
    base = (email.split("@")[0][:20] or "user").lower()
    username = base
    for _ in range(5):
        if not await db.scalar(select(User).where(User.username == username)):
            break
        username = f"{base}_{uuid.uuid4().hex[:6]}"
    user = User(
        username=username,
        nickname=data.nickname or base,
        email=email,
        status=UserStatus.NORMAL.value,
    )
    user.set_password(data.password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    _logger.info("user_registered_by_email", user_id=str(user.id), email=email)
    return user


async def list_bindings(db: AsyncSession, user: User) -> dict:
    """返回当前用户的全部绑定方式（自定义账号 / 邮箱 / 手机号 / 第三方）。"""
    providers = (
        await db.scalars(select(OAuthAccount.provider).where(OAuthAccount.user_id == user.id))
    ).all()
    return {
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "oauth": sorted(set(providers)),
    }


async def bind_email(db: AsyncSession, user: User, email: str, code: str) -> None:
    """绑定邮箱（需验证码）：已被其他账户占用时拒绝并明确提示。"""
    email = (email or "").strip().lower()
    rule = await get_email_register_rule(db)
    validate_email_rule(email, rule)
    if user.email and user.email.lower() == email:
        return
    if not await verify_code(email, code, "bind_email"):
        raise BizError(ErrorCode.VALIDATION, "邮箱验证码错误或已过期")
    dup = await db.scalar(
        select(User).where(func.lower(User.email) == email, User.id != user.id)
    )
    if dup:
        raise BizError(
            ErrorCode.CONFLICT,
            "该邮箱已绑定其他账号，请先用该邮箱登录，或登录原账号解绑后再绑定",
        )
    user.email = email
    await db.commit()
    _logger.info("user_bind_email", user_id=str(user.id), email=email)


async def bind_phone(db: AsyncSession, user: User, phone: str, code: str) -> None:
    """绑定手机号（需验证码）：已被其他账户占用时拒绝并明确提示。"""
    phone = (phone or "").strip()
    if not is_valid_phone(phone):
        raise BizError(ErrorCode.VALIDATION, "手机号格式不正确")
    if user.phone == phone:
        return
    if not await verify_code(phone, code, "bind_phone"):
        raise BizError(ErrorCode.VALIDATION, "手机号验证码错误或已过期")
    dup = await db.scalar(
        select(User).where(User.phone == phone, User.id != user.id)
    )
    if dup:
        raise BizError(
            ErrorCode.CONFLICT,
            "该手机号已绑定其他账号，请先用该手机号登录，或登录原账号解绑后再绑定",
        )
    user.phone = phone
    await db.commit()
    _logger.info("user_bind_phone", user_id=str(user.id), phone=phone)


async def unbind_email(db: AsyncSession, user: User) -> None:
    """解绑邮箱（保留自定义账号/手机号/第三方登录）。"""
    user.email = None
    await db.commit()
    _logger.info("user_unbind_email", user_id=str(user.id))


async def unbind_phone(db: AsyncSession, user: User) -> None:
    """解绑手机号。"""
    user.phone = None
    await db.commit()
    _logger.info("user_unbind_phone", user_id=str(user.id))


async def unbind_oauth(db: AsyncSession, user: User, provider: str) -> None:
    """解绑第三方账号。"""
    acct = await db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.user_id == user.id, OAuthAccount.provider == provider
        )
    )
    if not acct:
        raise BizError(ErrorCode.NOT_FOUND, "未绑定该第三方账号")
    await db.delete(acct)
    await db.commit()
    _logger.info("user_unbind_oauth", user_id=str(user.id), provider=provider)

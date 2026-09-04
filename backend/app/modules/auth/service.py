"""认证模块业务逻辑：注册/登录/刷新/注销/验证码/邮箱验证。"""

from __future__ import annotations

import asyncio
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

# 以**模块形式**导入，使调用点在运行时通过属性查找解析 send_email，
# 便于测试用 monkeypatch 替换（直接 from ... import send_email 会绑定旧引用）。
import app.tasks.email as email_tasks
from app.common.enums import UserStatus
from app.common.utils import generate_code, is_valid_email, is_valid_phone
from app.core.config import settings
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.core.redis import redis_delete, redis_get, redis_incr, redis_set
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

_CODE_TTL = settings.code_ttl_seconds  # 验证码有效期（可配置）
_RATE_LIMIT_PREFIX = "vcode:limit:"
_TRIES_PREFIX = "vcode:tries:"  # 验证码校验尝试次数（防暴力枚举）

# 验证码用途 → 邮件文案（缺了会把主题写成"【武汉大学】bind_email验证码"）
_PURPOSE_LABELS = {
    "register": "注册",
    "login": "登录",
    "reset": "重置密码",
    "bind": "绑定",
    "bind_email": "绑定邮箱",
    "bind_phone": "绑定手机号",
}


class _EmailDispatchTimeout(BizError):
    """邮件派发超时。

    与"确定失败"区分开：超时的那封邮件可能仍在后台线程里缓慢投递，
    调用方**不能**据此归还发送额度让用户立即重发，否则同一邮箱会收到两封验证码。
    """

    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.INTERNAL, message)


async def _dispatch_code_email(target: str, code: str, purpose: str) -> None:
    """把验证码投递到邮件队列。

    取舍说明：
    * ``SMTP_HOST`` 未配置 → 直接跳过（DEBUG 模式下验证码从响应回传，
      不发信是预期行为），仅记 warning；
    * 已配置但**派发失败** → 抛业务错误。此时验证码确实写进了 Redis，
      但用户永远收不到，若返回"已发送"就是欺骗用户，宁可让前端报错重试。

    ⚠️ 为何必须用 ``asyncio.to_thread`` 包一层
    ----------------------------------------
    Celery 的 ``delay()`` 在 broker / result backend **不可达**时不会立即失败，
    而是按默认策略同步重试（约 20 次 × 1 秒 ≈ 2 分钟）。它是纯同步阻塞调用，
    一旦直接写在 async 函数里，会把 uvicorn 的事件循环整个堵死 ——
    表现为用户点"发送验证码"后一直转圈，且**同一进程的所有请求全部无响应**。

    放进线程池执行后，即使 Celery 队列抖动，受阻的也只有这一个请求，
    不会波及其他用户。这是生产环境必须守住的一条底线。
    """
    if not settings.smtp_host:
        # 已开启"回传验证码"（本地联调 / 自动化测试）：拿不到邮件也能走通链路，
        # 此时跳过派发是预期行为。
        if settings.expose_verification_code:
            _logger.warning("code_email_skipped_smtp_unconfigured", target=target, purpose=purpose)
            return
        # 生产未配置邮件且又不回传验证码：验证码永远到不了用户手上。
        # 必须显式报错，绝不能返回"已发送"——那是对用户的欺骗，
        # 用户会一直等一封不存在的邮件。
        _logger.error("code_email_blocked_smtp_unconfigured", target=target, purpose=purpose)
        raise BizError(ErrorCode.INTERNAL, "邮件服务未配置，验证码无法送达，请联系管理员")

    label = _PURPOSE_LABELS.get(purpose, purpose)
    subject = f"【{settings.school_name}】{label}验证码"
    body = (
        f"您的{label}验证码是：{code}\n\n"
        f"有效期 {_CODE_TTL // 60} 分钟，请勿告知他人。\n"
        f"若非本人操作，请忽略此邮件。\n"
    )
    def _dispatch() -> str:
        # 优先 Celery 队列（解耦、可重试、生产推荐路径）。
        # broker 不可达（本地未起 Redis / 生产 broker 抖动）时，delay() 会因上面的
        # broker_connection_max_retries 配置快速抛错，此时降级为**内联直发**——
        # 直接执行任务体（smtplib 同步发送），保证验证码一定送达，不至于让
        # "收不到验证码"卡死注册/登录流程。
        try:
            email_tasks.send_email.delay(target, subject, body)
            return "queued"
        except Exception as exc:  # broker 不可达 / 队列故障
            _logger.warning(
                "email_dispatch_queue_unavailable_fallback_inline",
                target=target,
                purpose=purpose,
                error=str(exc),
            )
            try:
                result = email_tasks.send_email(target, subject, body)
            except Exception as inner:
                _logger.error(
                    "email_dispatch_inline_failed",
                    target=target,
                    purpose=purpose,
                    error=str(inner),
                )
                return "failed"
            return "inline" if (result and result.get("ok")) else "failed"

    try:
        # 双重保护：to_thread 避免阻塞事件循环，wait_for 限制单个请求的最长等待。
        # 即使队列彻底不可用 + 内联 SMTP 也超时，用户最多等 email_dispatch_timeout 秒拿到明确结果。
        mode = await asyncio.wait_for(
            asyncio.to_thread(_dispatch),
            timeout=settings.email_dispatch_timeout,
        )
    except TimeoutError:
        _logger.error(
            "code_email_dispatch_timeout",
            target=target,
            purpose=purpose,
            timeout=settings.email_dispatch_timeout,
        )
        # 本地联调豁免：已开启"回传验证码"时调用方不依赖邮件，
        # 队列故障不应阻断注册流程（否则本地/测试环境无法开发）。
        if settings.expose_verification_code:
            _logger.warning(
                "code_email_dispatch_ignored_debug_mode",
                target=target,
                purpose=purpose,
                reason="EXPOSE_VERIFICATION_CODE=true",
            )
            return
        # 超时用专用子类：send_code 据此判断"邮件可能迟到"，不归还发送额度
        raise _EmailDispatchTimeout("邮件服务繁忙，请稍后重试") from None
    except Exception as exc:
        _logger.error("code_email_dispatch_failed", target=target, purpose=purpose, error=str(exc))
        if settings.expose_verification_code:
            _logger.warning(
                "code_email_dispatch_ignored_debug_mode",
                target=target,
                purpose=purpose,
                reason="EXPOSE_VERIFICATION_CODE=true",
            )
            return
        raise BizError(ErrorCode.INTERNAL, "验证码发送失败，请稍后重试") from exc

    if mode == "failed":
        _logger.error("code_email_all_failed", target=target, purpose=purpose)
        if settings.expose_verification_code:
            return
        raise BizError(ErrorCode.INTERNAL, "验证码发送失败，请稍后重试")

    _logger.info("code_email_dispatched", target=target, purpose=purpose, mode=mode)


async def register(db: AsyncSession, data) -> User:
    """注册新用户（用户名唯一）。"""
    existing = await db.scalar(select(User).where(User.username == data.username))
    if existing:
        raise BizError(ErrorCode.CONFLICT, "用户名已存在")
    user = User(username=data.username, nickname=data.nickname or data.username)
    if data.email:
        email = (data.email or "").strip().lower()
        if not is_valid_email(email):
            raise BizError(ErrorCode.VALIDATION, "邮箱格式不正确")
        # 与邮箱注册保持同一套规则：后台可配的域名白名单 / 正则，
        # 避免「用户名注册」成为绕过校园邮箱限制的后门。
        rule = await get_email_register_rule(db)
        validate_email_rule(email, rule)
        dup = await db.scalar(select(User).where(func.lower(User.email) == email))
        if dup:
            raise BizError(ErrorCode.CONFLICT, "邮箱已被注册")
        user.email = email
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


async def authenticate(db: AsyncSession, account: str, password: str) -> User | None:
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
    expires_at = datetime.now(UTC) + timedelta(
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
    except Exception:
        # from None：不把 JWT 解码的内部异常链进对外错误，避免泄露令牌细节
        raise BizError(ErrorCode.UNAUTHORIZED, "refresh token 无效") from None
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
    target = (target or "").strip()
    # 邮箱统一小写：注册/绑定时会以 lower(email) 读取验证码，
    # 若此处不规范化，用户输入含大写字母就会取不到刚收到的验证码。
    if is_valid_email(target):
        target = target.lower()
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
    # 新验证码下发即清零尝试次数，避免上一轮的重试记录连坐新验证码
    await redis_delete(f"{_TRIES_PREFIX}{purpose}:{target}")
    # 入库存好之后再派发邮件：即使发信失败，重试也不会重复生成新码
    if is_mail:
        try:
            await _dispatch_code_email(target, code, purpose)
        except _EmailDispatchTimeout:
            raise  # 邮件可能仍在路上，不归还额度，避免用户立即重发收到两封
        except BizError:
            # 派发**确定**失败（一封都没发出去）：归还本窗口的发送额度，
            # 用户修正后立即可重试，而不是被"发送过于频繁"再拦 60 秒——
            # 没发出任何邮件的失败不该消耗频率配额。
            await redis_delete(limit_key)
            raise
    _logger.info("verification_code_sent", target=target, purpose=purpose)
    return code


async def verify_code(target: str, code: str, purpose: str) -> bool:
    """校验验证码（成功即失效）。

    6 位数字的组合空间只有 100 万，有效期内若不限制尝试次数可被暴力枚举，
    因此累计错误次数达到上限就作废该验证码，迫使用户重新获取。
    比较使用恒定时间算法，避免通过响应耗时逐位试探。
    """
    target = (target or "").strip()
    # 与 send_code 保持同一套规范化规则，避免大小写导致取不到验证码
    if is_valid_email(target):
        target = target.lower()
    key = f"vcode:{purpose}:{target}"
    tries_key = f"{_TRIES_PREFIX}{purpose}:{target}"

    stored = await redis_get(key)
    if not stored:
        return False

    tries = await redis_incr(tries_key, ttl=_CODE_TTL)
    if tries > settings.code_max_attempts:
        await redis_set(key, "", ttl=1)
        await redis_delete(tries_key)
        _logger.warning("verification_code_locked", target=target, purpose=purpose)
        return False

    if not secrets.compare_digest(stored, code):
        return False

    # 校验成功：验证码与尝试计数一并清除
    await redis_set(key, "", ttl=1)
    await redis_delete(tries_key)
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
    except Exception:
        raise BizError(ErrorCode.VALIDATION, "验证链接无效或已过期") from None
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

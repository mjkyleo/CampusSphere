"""认证路由：/api/auth/*。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import EmailRegisterConfig
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import BizError, ErrorCode
from app.core.response import ApiResponse
from app.modules.audit.actions import ActorType, AuditAction, AuditResult
from app.modules.audit.service import record_audit_log
from app.modules.auth.captcha import consume_ticket, generate_slider, issue_ticket, verify_slider
from app.modules.auth.deps import get_current_user
from app.modules.auth.geetest import captcha_provider, geetest_enabled, verify_geetest
from app.modules.auth.models import User
from app.modules.auth.oauth import (
    bind_oauth,
    generate_oauth_state,
    qq_login,
    verify_oauth_state,
    wechat_login,
)
from app.modules.auth.schemas import (
    BindEmailRequest,
    BindingsOut,
    BindOAuthRequest,
    BindPhoneRequest,
    EmailRegisterRequest,
    EmailRegisterResponse,
    GeetestVerifyRequest,
    LoginRequest,
    PhoneLoginRequest,
    RefreshRequest,
    RegisterRequest,
    SendCodeOut,
    SendCodeRequest,
    SliderCaptchaOut,
    SliderVerifyOut,
    SliderVerifyRequest,
    TokenResponse,
    UnbindOAuthRequest,
    UserOut,
    VerifyEmailRequest,
)
from app.modules.auth.service import (
    bind_email,
    bind_phone,
    issue_tokens,
    list_bindings,
    login,
    logout,
    phone_login,
    refresh_token,
    register,
    register_by_email,
    send_code,
    unbind_email,
    unbind_oauth,
    unbind_phone,
    verify_email,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _audit_auth(
    request: Request | None,
    *,
    action: str,
    result: str = AuditResult.SUCCESS,
    actor_id: str | None = None,
    actor_label: str = "",
    actor_type: str = ActorType.USER,
    detail: dict | None = None,
) -> None:
    """记录认证类审计日志。

    审计是旁路能力 —— ``record_audit_log`` 内部已保证任何异常都不会向外抛出，
    因此这里可以放心调用，不必再包一层 try/except。
    """
    await record_audit_log(
        action=action,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_label=actor_label,
        result=result,
        detail=detail,
        request=request,
    )


@router.post("/register", response_model=ApiResponse[UserOut])
async def register_user(
    data: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    try:
        user = await register(db, data)
    except BizError as exc:
        await _audit_auth(
            request,
            action=AuditAction.REGISTER_FAILED,
            result=AuditResult.FAILURE,
            actor_label=data.username,
            detail={"reason": exc.message},
        )
        raise
    await _audit_auth(
        request,
        action=AuditAction.REGISTER,
        actor_id=str(user.id),
        actor_label=user.username,
        detail={"email": data.email or "", "phone": data.phone or ""},
    )
    return ApiResponse.ok(data=UserOut.model_validate(user))


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login_user(
    data: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    """统一登录：账号（邮箱 / 手机号 / 自定义账号）+ 密码。"""
    account = data.account or data.username
    if not account:
        await _audit_auth(
            request,
            action=AuditAction.LOGIN_FAILED,
            result=AuditResult.FAILURE,
            detail={"reason": "账号为空"},
        )
        raise BizError(ErrorCode.VALIDATION, "账号不能为空")
    try:
        tokens = await login(db, account, data.password)
    except BizError as exc:
        # 登录失败是安全事件，必须留痕（撞库、密码爆破都从这里看出来）
        await _audit_auth(
            request,
            action=AuditAction.LOGIN_FAILED,
            result=AuditResult.FAILURE,
            actor_label=account,
            detail={"reason": exc.message},
        )
        raise
    await _audit_auth(
        request, action=AuditAction.LOGIN, actor_label=account
    )
    return ApiResponse.ok(data=TokenResponse(**tokens))


@router.post("/phone-login", response_model=ApiResponse[TokenResponse])
async def phone_login_user(
    data: PhoneLoginRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    try:
        tokens = await phone_login(db, data.target, data.code)
    except BizError as exc:
        await _audit_auth(
            request,
            action=AuditAction.PHONE_LOGIN,
            result=AuditResult.FAILURE,
            actor_label=data.target,
            detail={"reason": exc.message},
        )
        raise
    await _audit_auth(
        request, action=AuditAction.PHONE_LOGIN, actor_label=data.target
    )
    return ApiResponse.ok(data=TokenResponse(**tokens))


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh_user_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    tokens = await refresh_token(db, data.refresh_token)
    return ApiResponse.ok(data=TokenResponse(**tokens))


@router.post("/logout", response_model=ApiResponse[None])
async def logout_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    auth = request.headers.get("Authorization", "")
    access = auth[7:] if auth.startswith("Bearer ") else ""
    # refresh token 来自 body 或 header X-Refresh-Token
    refresh = request.headers.get("X-Refresh-Token", "")
    await logout(db, access, refresh)
    await _audit_auth(
        request,
        action=AuditAction.LOGOUT,
        actor_id=str(current_user.id),
        actor_label=current_user.username,
    )
    return ApiResponse.ok(message="已注销")


# ---------------------------------------------------------------------------
# 滑块验证：发送验证码前的防滥用闸门
# ---------------------------------------------------------------------------
@router.get("/captcha/config", response_model=ApiResponse[dict])
async def captcha_config():
    """公开只读：验证码开关与当前生效的提供方，供前端决定渲染哪种验证。

    ``provider`` 取值：
      * ``geetest`` —— 已配置极验 captcha_id/key，前端渲染极验组件
      * ``builtin`` —— 未接入第三方，使用服务端生成的拼图滑块

    前端只认这个字段，不自己判断"有没有极验"，
    避免两端对同一份配置产生不同理解。
    """
    provider = captcha_provider()
    return ApiResponse.ok(
        data={
            "enabled": settings.captcha_enabled,
            "provider": provider,
            # 仅 geetest 模式下需要，builtin 时为空串（前端不会用到）
            "geetest_id": settings.geetest_captcha_id if provider == "geetest" else "",
        }
    )


@router.post("/captcha/geetest/verify", response_model=ApiResponse[SliderVerifyOut])
async def captcha_geetest_verify(data: GeetestVerifyRequest):
    """极验二次校验：通过后签发一次性票据（供 send-code 使用）。

    票据机制与自建滑块**完全一致**，因此下游 send-code 不需要区分
    用户是通过哪种方式完成的验证 —— 换 provider 对业务代码透明。
    """
    if not geetest_enabled():
        raise BizError(ErrorCode.VALIDATION, "当前未启用极验验证")

    ok, reason = await verify_geetest(
        data.lot_number, data.captcha_output, data.pass_token, data.gen_time
    )
    if not ok:
        # 不回传 reason：避免给攻击者提供调整参数的反馈
        raise BizError(ErrorCode.VALIDATION, "人机验证未通过，请重试")

    return ApiResponse.ok(
        message="验证通过",
        data=SliderVerifyOut(
            ticket=await issue_ticket(),
            expires_in=settings.captcha_ticket_ttl_seconds,
        ),
    )


@router.get("/captcha/slider", response_model=ApiResponse[SliderCaptchaOut])
async def captcha_slider():
    """获取一次滑块验证（背景图 + 拼图块）。

    缺口的横坐标只保存在服务端，响应中仅包含纵坐标 y，
    前端据此把拼图块放在同一水平线上。
    """
    return ApiResponse.ok(data=SliderCaptchaOut(**await generate_slider()))


@router.post("/captcha/verify", response_model=ApiResponse[SliderVerifyOut])
async def captcha_verify(data: SliderVerifyRequest):
    """校验滑块拖动结果，通过则签发一次性票据（供 send-code 使用）。"""
    ticket = await verify_slider(
        data.token, data.offset_x, data.track, data.elapsed_ms
    )
    return ApiResponse.ok(
        message="验证通过",
        data=SliderVerifyOut(
            ticket=ticket, expires_in=settings.captcha_ticket_ttl_seconds
        ),
    )


@router.post("/send-code", response_model=ApiResponse[SendCodeOut])
async def send_verification_code(data: SendCodeRequest, request: Request):
    """发送验证码（邮箱/手机号，purpose 区分用途）。

    开启滑块验证时，必须携带 ``/captcha/verify`` 签发的一次性票据，
    否则拒绝发送——避免脚本绕过滑块直接刷验证码轰炸邮箱/手机。

    默认**绝不**回传验证码（仅通过邮件送达）；
    仅当开启 ``EXPOSE_VERIFICATION_CODE`` 时回传 debug_code，供本地联调与自动化测试使用。
    """
    if settings.captcha_enabled and not await consume_ticket(data.captcha_ticket):
        await _audit_auth(
            request,
            action=AuditAction.SEND_CODE_FAILED,
            result=AuditResult.FAILURE,
            actor_label=data.target,
            detail={"reason": "未完成人机验证", "purpose": data.purpose},
        )
        raise BizError(ErrorCode.VALIDATION, "请先完成滑块验证")
    try:
        code = await send_code(
            data.target, data.purpose, limit_per_minute=settings.code_send_limit_per_minute
        )
    except BizError as exc:
        # 发送失败也要留痕：频率超限、邮箱域名不合法等都可能是对抗性行为
        await _audit_auth(
            request,
            action=AuditAction.SEND_CODE_FAILED,
            result=AuditResult.FAILURE,
            actor_label=data.target,
            detail={"reason": exc.message, "purpose": data.purpose},
        )
        raise
    await _audit_auth(
        request,
        action=AuditAction.SEND_CODE,
        actor_label=data.target,
        detail={"purpose": data.purpose},
    )
    # 由独立的 ``EXPOSE_VERIFICATION_CODE`` 开关控制（默认 false）。
    #
    # 这里**不再**用 `not settings.smtp_host` 作为回传条件：那会让"未配置 SMTP
    # 的生产环境"把 6 位验证码直接明文返回给调用方，任何人都能绕过邮箱验证
    # 注册任意账号。
    # 也不复用 DEBUG：DEBUG 会连带关闭管理员网关校验，用它会把安全测试架空。
    debug_code = code if settings.expose_verification_code else None
    return ApiResponse.ok(
        message="验证码已发送" + ("（测试模式：见响应 debug_code）" if debug_code else ""),
        data=SendCodeOut(debug_code=debug_code),
    )


@router.get("/email-config", response_model=ApiResponse[EmailRegisterConfig])
async def email_register_config(db: AsyncSession = Depends(get_db)):
    """公开只读：邮箱注册规则（是否开启 + 允许域名/正则），供注册页动态展示。"""
    from app.modules.admin.service import get_email_register_config

    cfg = await get_email_register_config(db)
    return ApiResponse.ok(data=EmailRegisterConfig(**cfg))


@router.post("/verify-email", response_model=ApiResponse[UserOut])
async def verify_email_endpoint(data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    user = await verify_email(db, data.token)
    return ApiResponse.ok(data=UserOut.model_validate(user))


@router.get("/wechat/state", response_model=ApiResponse[str])
async def wechat_oauth_state():
    """前端获取 state（防 CSRF）。"""
    state = await generate_oauth_state("wechat")
    return ApiResponse.ok(data=state)


@router.get("/qq/state", response_model=ApiResponse[str])
async def qq_oauth_state():
    state = await generate_oauth_state("qq")
    return ApiResponse.ok(data=state)


@router.get("/wechat/callback", response_model=ApiResponse[TokenResponse])
async def wechat_callback(code: str, state: str = "", db: AsyncSession = Depends(get_db)):
    if not await verify_oauth_state("wechat", state):
        raise BizError(ErrorCode.FORBIDDEN, "state 校验失败")
    user, _ = await wechat_login(db, code)
    tokens = await issue_tokens(db, user)
    return ApiResponse.ok(data=TokenResponse(**tokens))


@router.get("/qq/callback", response_model=ApiResponse[TokenResponse])
async def qq_callback(
    code: str, state: str = "", db: AsyncSession = Depends(get_db)
):
    if not await verify_oauth_state("qq", state):
        raise BizError(ErrorCode.FORBIDDEN, "state 校验失败")
    user, _ = await qq_login(db, code)
    tokens = await issue_tokens(db, user)
    return ApiResponse.ok(data=TokenResponse(**tokens))


@router.post("/email-register", response_model=ApiResponse[EmailRegisterResponse])
async def email_register(
    data: EmailRegisterRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    """邮箱验证码注册：校验后台邮箱规则 + 验证码，自动生成自定义账号并签发令牌（注册即登录）。"""
    try:
        user = await register_by_email(db, data)
    except BizError as exc:
        await _audit_auth(
            request,
            action=AuditAction.EMAIL_REGISTER,
            result=AuditResult.FAILURE,
            actor_label=data.email,
            detail={"reason": exc.message},
        )
        raise
    tokens = await issue_tokens(db, user)
    await _audit_auth(
        request,
        action=AuditAction.EMAIL_REGISTER,
        actor_id=str(user.id),
        actor_label=user.email,
        detail={"username": user.username},
    )
    return ApiResponse.ok(
        message="注册成功，已自动登录",
        data=EmailRegisterResponse(email=user.email, username=user.username, **tokens),
    )


@router.get("/bindings", response_model=ApiResponse[BindingsOut])
async def get_bindings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询当前账户的绑定方式（自定义账号/邮箱/手机号/第三方）。"""
    return ApiResponse.ok(data=BindingsOut(**await list_bindings(db, user)))


@router.post("/bind/email", response_model=ApiResponse[None])
async def bind_email_endpoint(
    data: BindEmailRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """补充绑定邮箱（需邮箱验证码，purpose=bind_email）。"""
    await bind_email(db, user, data.email, data.code)
    return ApiResponse.ok(message="邮箱绑定成功")


@router.post("/bind/phone", response_model=ApiResponse[None])
async def bind_phone_endpoint(
    data: BindPhoneRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """补充绑定手机号（需短信验证码，purpose=bind_phone）。"""
    await bind_phone(db, user, data.phone, data.code)
    return ApiResponse.ok(message="手机号绑定成功")


@router.post("/bind/oauth", response_model=ApiResponse[None])
async def bind_oauth_endpoint(
    data: BindOAuthRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """补充绑定 QQ / 微信（需 OAuth 授权码 + state 防 CSRF）。"""
    if data.state and not await verify_oauth_state(data.provider, data.state):
        raise BizError(ErrorCode.FORBIDDEN, "state 校验失败")
    await bind_oauth(db, user, data.provider, data.code, data.redirect_uri)
    return ApiResponse.ok(message="绑定成功")


@router.delete("/unbind/email", response_model=ApiResponse[None])
async def unbind_email_endpoint(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await unbind_email(db, user)
    return ApiResponse.ok(message="邮箱已解绑")


@router.delete("/unbind/phone", response_model=ApiResponse[None])
async def unbind_phone_endpoint(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await unbind_phone(db, user)
    return ApiResponse.ok(message="手机号已解绑")


@router.delete("/unbind/oauth", response_model=ApiResponse[None])
async def unbind_oauth_endpoint(
    data: UnbindOAuthRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await unbind_oauth(db, user, data.provider)
    return ApiResponse.ok(message="第三方账号已解绑")

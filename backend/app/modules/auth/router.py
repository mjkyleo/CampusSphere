"""认证路由：/api/auth/*。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import EmailRegisterConfig
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import BizError, ErrorCode
from app.core.response import ApiResponse
from app.modules.auth.captcha import consume_ticket, generate_slider, verify_slider
from app.modules.auth.deps import get_current_user
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


@router.post("/register", response_model=ApiResponse[UserOut])
async def register_user(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await register(db, data)
    return ApiResponse.ok(data=UserOut.model_validate(user))


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login_user(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """统一登录：账号（邮箱 / 手机号 / 自定义账号）+ 密码。"""
    account = data.account or data.username
    if not account:
        raise BizError(ErrorCode.VALIDATION, "账号不能为空")
    tokens = await login(db, account, data.password)
    return ApiResponse.ok(data=TokenResponse(**tokens))


@router.post("/phone-login", response_model=ApiResponse[TokenResponse])
async def phone_login_user(data: PhoneLoginRequest, db: AsyncSession = Depends(get_db)):
    tokens = await phone_login(db, data.target, data.code)
    return ApiResponse.ok(data=TokenResponse(**tokens))


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh_user_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    tokens = await refresh_token(db, data.refresh_token)
    return ApiResponse.ok(data=TokenResponse(**tokens))


@router.post("/logout", response_model=ApiResponse[None])
async def logout_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    auth = request.headers.get("Authorization", "")
    access = auth[7:] if auth.startswith("Bearer ") else ""
    # refresh token 来自 body 或 header X-Refresh-Token
    refresh = request.headers.get("X-Refresh-Token", "")
    await logout(db, access, refresh)
    return ApiResponse.ok(message="已注销")


# ---------------------------------------------------------------------------
# 滑块验证：发送验证码前的防滥用闸门
# ---------------------------------------------------------------------------
@router.get("/captcha/config", response_model=ApiResponse[dict])
async def captcha_config():
    """公开只读：滑块验证是否开启，供前端决定是否需要弹出滑块。"""
    return ApiResponse.ok(data={"enabled": settings.captcha_enabled})


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
async def send_verification_code(data: SendCodeRequest):
    """发送验证码（邮箱/手机号，purpose 区分用途）。

    开启滑块验证时，必须携带 ``/captcha/verify`` 签发的一次性票据，
    否则拒绝发送——避免脚本绕过滑块直接刷验证码轰炸邮箱/手机。

    开发/测试模式（settings.debug=true）下响应中直接返回 debug_code，
    便于无邮件/短信通道时验证注册登录流程；生产模式不返回，仅真实送达。
    """
    if settings.captcha_enabled and not await consume_ticket(data.captcha_ticket):
        raise BizError(ErrorCode.VALIDATION, "请先完成滑块验证")
    code = await send_code(data.target, data.purpose)
    # 开发模式或尚未配置邮件/短信发送通道时，响应中直接返回验证码，便于测试联调；
    # 生产环境接入 SMTP 后 debug_code 恒为 null，验证码仅通过邮件送达。
    debug_code = code if (settings.debug or not settings.smtp_host) else None
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
async def email_register(data: EmailRegisterRequest, db: AsyncSession = Depends(get_db)):
    """邮箱验证码注册：校验后台邮箱规则 + 验证码，自动生成自定义账号并签发令牌（注册即登录）。"""
    user = await register_by_email(db, data)
    tokens = await issue_tokens(db, user)
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

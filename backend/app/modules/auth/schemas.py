"""认证模块 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

try:  # EmailStr 需要 email-validator，降级为 str
    from pydantic import EmailStr
except Exception:
    EmailStr = str  # type: ignore


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    email: str | None = None
    phone: str | None = None
    nickname: str | None = None


class LoginRequest(BaseModel):
    username: str | None = None
    account: str | None = None  # 统一账号：邮箱 / 手机号 / 自定义账号
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class SendCodeRequest(BaseModel):
    target: str = Field(description="手机号或邮箱")
    purpose: str = Field(default="login", description="login/register/email")
    captcha_ticket: str | None = Field(
        default=None,
        description="滑块验证票据（captcha_enabled 时必填，由 /captcha/verify 签发）",
    )


class SendCodeOut(BaseModel):
    """发送验证码响应。开发/测试模式（debug=true）返回 debug_code 便于本地验证；
    生产环境 debug_code 恒为 null，验证码只能通过邮件/短信真实送达。"""

    debug_code: str | None = None
    expires_in: int = 300


# ---------------------------------------------------------------------------
# 滑块验证
# ---------------------------------------------------------------------------
class SliderCaptchaOut(BaseModel):
    """滑块验证载荷：两张 base64 图片 + 画布尺寸。

    注意：缺口的**横坐标不会下发**（仅服务端保存），只有纵坐标 y 需要下发，
    前端据此把滑块放在同一水平线上。
    """

    token: str = Field(description="本次验证令牌，校验时回传")
    background: str = Field(description="带缺口的背景图（data URI）")
    slider: str = Field(description="拼图块（data URI，透明 PNG）")
    width: int = Field(description="画布宽度（px）")
    height: int = Field(description="画布高度（px）")
    slider_size: int = Field(description="滑块边长（px）")
    y: int = Field(description="缺口纵坐标（px），滑块需保持同一水平线")
    expires_in: int = Field(description="令牌有效期（秒）")


class SliderVerifyRequest(BaseModel):
    token: str = Field(description="generate_slider 返回的令牌")
    offset_x: float = Field(description="滑块相对画布左边缘的位移（px）")
    track: list[list[float]] = Field(
        default_factory=list,
        description="拖动轨迹 [[t_ms, x, y], ...]，用于识别脚本行为",
    )
    elapsed_ms: int = Field(default=0, description="从开始拖到松手的总耗时（毫秒）")


class SliderVerifyOut(BaseModel):
    """校验通过后的票据，需在调用 send-code 时回传（一次性）。"""

    ticket: str
    expires_in: int


class VerifyCodeRequest(BaseModel):
    target: str
    code: str
    purpose: str = "login"


class VerifyEmailRequest(BaseModel):
    token: str = Field(description="邮箱验证 JWT")


class PhoneLoginRequest(BaseModel):
    target: str
    code: str


class OAuthCallbackResponse(TokenResponse):
    is_new: bool = False


class EmailRegisterResponse(TokenResponse):
    """邮箱注册响应：在令牌基础上附带新生成的账号信息，便于前端直接展示。"""

    email: str | None = None
    username: str


class UserOut(BaseModel):
    id: UUID
    username: str
    email: str | None = None
    phone: str | None = None
    nickname: str
    avatar: str | None = None
    status: int
    created_at: datetime

    model_config = {"from_attributes": True}


class EmailRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    nickname: str | None = Field(default=None, max_length=32)
    code: str = Field(description="邮箱验证码（purpose=register）")


class BindEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(description="邮箱验证码（purpose=bind_email）")


class BindPhoneRequest(BaseModel):
    phone: str
    code: str = Field(description="短信验证码（purpose=bind_phone）")


class BindOAuthRequest(BaseModel):
    provider: str = Field(description="wechat/qq")
    code: str
    redirect_uri: str = ""
    state: str | None = Field(default=None, description="OAuth state（防 CSRF）")


class UnbindOAuthRequest(BaseModel):
    provider: str = Field(description="wechat/qq")


class BindingsOut(BaseModel):
    username: str
    email: str | None = None
    phone: str | None = None
    oauth: list[str] = []

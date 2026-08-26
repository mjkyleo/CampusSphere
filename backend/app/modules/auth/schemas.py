"""认证模块 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

try:  # EmailStr 需要 email-validator，降级为 str
    from pydantic import EmailStr  # noqa: F811
except Exception:  # noqa
    EmailStr = str  # type: ignore


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    email: Optional[str] = None
    phone: Optional[str] = None
    nickname: Optional[str] = None


class LoginRequest(BaseModel):
    username: Optional[str] = None
    account: Optional[str] = None  # 统一账号：邮箱 / 手机号 / 自定义账号
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


class SendCodeOut(BaseModel):
    """发送验证码响应。开发/测试模式（debug=true）返回 debug_code 便于本地验证；
    生产环境 debug_code 恒为 null，验证码只能通过邮件/短信真实送达。"""

    debug_code: Optional[str] = None
    expires_in: int = 300


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


class UserOut(BaseModel):
    id: UUID
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    nickname: str
    avatar: Optional[str] = None
    status: int
    created_at: datetime

    model_config = {"from_attributes": True}


class EmailRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    nickname: Optional[str] = Field(default=None, max_length=32)
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
    state: Optional[str] = Field(default=None, description="OAuth state（防 CSRF）")


class UnbindOAuthRequest(BaseModel):
    provider: str = Field(description="wechat/qq")


class BindingsOut(BaseModel):
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    oauth: list[str] = []

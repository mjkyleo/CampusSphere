"""认证模块 ORM 模型：User、OAuthAccount、RefreshToken、VerificationCode。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import UserStatus
from app.common.models import Base, PKMixin, SoftDeleteMixin, TimestampMixin


class User(Base, PKMixin, TimestampMixin, SoftDeleteMixin):
    """平台用户。"""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), unique=True, index=True, default=None)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True, default=None)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    nickname: Mapped[str] = mapped_column(String(64), default="")
    avatar: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    status: Mapped[int] = mapped_column(Integer, default=UserStatus.NORMAL.value, index=True)

    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    def set_password(self, password: str) -> None:
        from app.core.security import hash_password

        self.password_hash = hash_password(password)

    def check_password(self, password: str) -> bool:
        from app.core.security import verify_password

        return verify_password(password, self.password_hash)


class OAuthAccount(Base, PKMixin, TimestampMixin):
    """第三方账号绑定（微信/QQ）。"""

    __tablename__ = "oauth_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(16), index=True)  # wechat / qq
    provider_openid: Mapped[str] = mapped_column(String(64), index=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="oauth_accounts")


class RefreshToken(Base, PKMixin, TimestampMixin):
    """刷新令牌记录（用于注销/吊销追踪）。"""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class VerificationCode(Base, PKMixin, TimestampMixin):
    """短信/邮箱验证码。"""

    __tablename__ = "verification_codes"

    target: Mapped[str] = mapped_column(String(128), index=True)  # phone or email
    code: Mapped[str] = mapped_column(String(8))
    purpose: Mapped[str] = mapped_column(String(16), index=True)  # login / register / email
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)

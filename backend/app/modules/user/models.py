"""用户模块 ORM 模型：UserProfile。"""

from __future__ import annotations

from sqlalchemy import UUID, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, PKMixin, TimestampMixin
from app.modules.auth.models import User


class UserProfile(Base, PKMixin, TimestampMixin):
    """用户扩展资料。"""

    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    bio: Mapped[str] = mapped_column(String(512), default="")
    school_major: Mapped[str] = mapped_column(String(64), default="")
    campus: Mapped[str] = mapped_column(String(64), default="")
    contact_wx: Mapped[str] = mapped_column(String(64), default="")
    grade: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship()

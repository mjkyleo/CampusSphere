"""资源共享 ORM 模型。"""

from __future__ import annotations

from sqlalchemy import UUID, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, PKMixin, TimestampMixin


class ShareResource(Base, PKMixin, TimestampMixin):
    """共享资源（学习资料等）。"""

    __tablename__ = "share_resources"

    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    file_key: Mapped[str] = mapped_column(String(255), default="")  # 对象存储 key
    category: Mapped[str] = mapped_column(String(32), default="other")
    downloads: Mapped[int] = mapped_column(Integer, default=0)

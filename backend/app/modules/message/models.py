"""消息模块 ORM 模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, PKMixin, TimestampMixin


class Conversation(Base, PKMixin, TimestampMixin):
    """会话（单聊/群聊/交易会话）。"""

    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("conv_type", "related_id", name="uq_conv_type_related"),)

    conv_type: Mapped[str] = mapped_column(String(16), default="direct", index=True)
    related_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", lazy="selectin"
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", lazy="selectin"
    )


class Participant(Base, PKMixin, TimestampMixin):
    """会话参与者（含已读游标）。"""

    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_conv_user"),
    )

    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    last_read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)

    conversation: Mapped["Conversation"] = relationship(back_populates="participants")


class Message(Base, PKMixin, TimestampMixin):
    """消息（文本/图片/文件）。"""

    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    sender_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    type: Mapped[int] = mapped_column(Integer, default=0, comment="0文本/1图片/2文件")
    content: Mapped[str] = mapped_column(Text, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

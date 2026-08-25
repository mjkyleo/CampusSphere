"""二手物品模块 ORM 模型。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import UUID, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, PKMixin, SoftDeleteMixin, TimestampMixin


class Item(Base, PKMixin, TimestampMixin, SoftDeleteMixin):
    """二手物品。"""

    __tablename__ = "items"

    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(String(1024), default="")
    price: Mapped[int] = mapped_column(Integer, default=0, comment="单位：分")
    category: Mapped[str] = mapped_column(String(32), index=True, default="other")
    status: Mapped[int] = mapped_column(Integer, default=0, index=True)  # ItemStatus

    images: Mapped[list["ItemImage"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ItemImage.sort_order",
    )
    trade_sessions: Mapped[list["TradeSession"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", lazy="selectin"
    )


class ItemImage(Base, PKMixin, TimestampMixin):
    """物品图片（对象存储 key）。"""

    __tablename__ = "item_images"

    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE"), index=True
    )
    object_key: Mapped[str] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    item: Mapped["Item"] = relationship(back_populates="images")


class TradeSession(Base, PKMixin, TimestampMixin):
    """交易会话（买家-卖家撮合）。"""

    __tablename__ = "trade_sessions"

    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE"), index=True
    )
    buyer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    seller_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    status: Mapped[int] = mapped_column(Integer, default=0, index=True)  # TradeStatus
    conversation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    item: Mapped["Item"] = relationship(back_populates="trade_sessions")

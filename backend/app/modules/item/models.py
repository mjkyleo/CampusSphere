"""二手物品模块 ORM 模型。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, text
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

    images: Mapped[list[ItemImage]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ItemImage.sort_order",
    )
    trade_sessions: Mapped[list[TradeSession]] = relationship(
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

    item: Mapped[Item] = relationship(back_populates="images")


class TradeSession(Base, PKMixin, TimestampMixin):
    """交易会话（买家-卖家撮合）。

    并发安全：服务层用「带旧状态条件的 UPDATE」原子抢占物品（ON_SALE→RESERVED），
    这里再补一层**部分唯一索引**兜底——同一物品同时最多只能有一个"进行中"的
    交易会话。终态（COMPLETED/CANCELLED）不参与约束，因此同一物品的历史成交
    记录仍可保留多条。
    """

    __tablename__ = "trade_sessions"
    # 活跃状态：PENDING(0) 与 IN_PROGRESS(1)；与 TradeStatus 取值保持一致。
    __table_args__ = (
        Index(
            "uq_trade_session_active_item",
            "item_id",
            unique=True,
            sqlite_where=text("status IN (0, 1)"),
            postgresql_where=text("status IN (0, 1)"),
        ),
    )

    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE"), index=True
    )
    buyer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    seller_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    status: Mapped[int] = mapped_column(Integer, default=0, index=True)  # TradeStatus
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    item: Mapped[Item] = relationship(back_populates="trade_sessions")

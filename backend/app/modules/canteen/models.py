"""食堂模块 ORM 模型。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, PKMixin, TimestampMixin


class Canteen(Base, PKMixin, TimestampMixin):
    """食堂。"""

    __tablename__ = "canteens"

    name: Mapped[str] = mapped_column(String(64), index=True)
    location: Mapped[str] = mapped_column(String(128), default="")
    image: Mapped[str] = mapped_column(String(512), default="")

    stalls: Mapped[list["Stall"]] = relationship(
        back_populates="canteen", cascade="all, delete-orphan", lazy="selectin"
    )


class Stall(Base, PKMixin, TimestampMixin):
    """摊位。"""

    __tablename__ = "stalls"

    canteen_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("canteens.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64))
    image: Mapped[str] = mapped_column(String(512), default="")

    canteen: Mapped["Canteen"] = relationship(back_populates="stalls")
    dishes: Mapped[list["Dish"]] = relationship(
        back_populates="stall", cascade="all, delete-orphan", lazy="selectin"
    )


class Dish(Base, PKMixin, TimestampMixin):
    """菜品。"""

    __tablename__ = "dishes"

    stall_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stalls.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64), index=True)
    price: Mapped[int] = mapped_column(Integer, default=0, comment="单位：分")
    image: Mapped[str] = mapped_column(String(512), default="")

    stall: Mapped["Stall"] = relationship(back_populates="dishes")
    reviews: Mapped[list["CanteenReview"]] = relationship(
        back_populates="dish", cascade="all, delete-orphan", lazy="selectin"
    )


class CanteenReview(Base, PKMixin, TimestampMixin):
    """菜品评价。"""

    __tablename__ = "canteen_reviews"

    dish_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dishes.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer, default=5)
    content: Mapped[str] = mapped_column(Text, default="")

    dish: Mapped["Dish"] = relationship(back_populates="reviews")

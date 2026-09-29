"""食堂模块 ORM 模型。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, PKMixin, TimestampMixin
from app.common.types import JsonList


class Canteen(Base, PKMixin, TimestampMixin):
    """食堂。

    维度说明（与武大实际结构对齐，全部由后台 canteen.config 枚举驱动）：

    - ``campus``：学部（文理学部 / 工学部 / 信息学部 / 医学部）
    - ``zone``：餐饮区（梅园 / 桂园 / 枫园 / 湖滨 / …）
    - ``canteen_type``：类型（学生大伙食堂 / 风味食堂 / 教工食堂）
    - ``floor``：楼层（如 "1F"、"2F"）
    - ``semester``：可选学期；为空表示长期开放（不随学期变化）
    """

    __tablename__ = "canteens"

    name: Mapped[str] = mapped_column(String(64), index=True)
    location: Mapped[str] = mapped_column(String(128), default="")
    image: Mapped[str] = mapped_column(String(512), default="")
    # 学部 —— 一级筛选维度
    campus: Mapped[str] = mapped_column(String(32), default="", index=True)
    # 餐饮区 —— 二级筛选维度（挂在学部下）
    zone: Mapped[str] = mapped_column(String(32), default="", index=True)
    # 类型（学生大伙 / 风味 / 教工）
    canteen_type: Mapped[str] = mapped_column(String(32), default="", index=True)
    # 楼层
    floor: Mapped[str] = mapped_column(String(32), default="")
    # 简介
    description: Mapped[str] = mapped_column(Text, default="")
    # 特色标签（如 ["便宜", "不挤"]）
    features: Mapped[list[str]] = mapped_column(JsonList, default=list)
    # 招牌菜（如 ["热干面", "豆皮"]）
    popular_dishes: Mapped[list[str]] = mapped_column(JsonList, default=list)
    # 营业时间（如 "07:00-20:00"）
    opening_hours: Mapped[str] = mapped_column(String(64), default="")
    # 学期；空表示长期开放
    semester: Mapped[str] = mapped_column(String(32), default="", index=True)

    stalls: Mapped[list[Stall]] = relationship(
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

    canteen: Mapped[Canteen] = relationship(back_populates="stalls")
    dishes: Mapped[list[Dish]] = relationship(
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

    stall: Mapped[Stall] = relationship(back_populates="dishes")
    reviews: Mapped[list[CanteenReview]] = relationship(
        # P2-17：不用模型级 selectin——Dish 会被 canteen 列表批量加载，
        # eager 装载等于每次列表把全库菜品评价拉进内存。删除菜品时的
        # 级联清理由 flush 内按需惰性加载 + DB 级 ON DELETE CASCADE 完成。
        back_populates="dish", cascade="all, delete-orphan"
    )


class CanteenReview(Base, PKMixin, TimestampMixin):
    """菜品评价。

    P1-7：同一用户对同一菜品仅允许一条评价，命名唯一索引兜底并发双插
    （同 course_reviews 的 uq_course_review_user）。
    """

    __tablename__ = "canteen_reviews"
    __table_args__ = (
        Index("uq_canteen_review_user", "dish_id", "user_id", unique=True),
    )

    dish_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dishes.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer, default=5)
    content: Mapped[str] = mapped_column(Text, default="")

    dish: Mapped[Dish] = relationship(back_populates="reviews")

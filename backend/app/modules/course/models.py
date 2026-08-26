"""课程模块 ORM 模型。"""

from __future__ import annotations

from sqlalchemy import UUID, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, PKMixin, TimestampMixin


class Course(Base, PKMixin, TimestampMixin):
    """课程。"""

    __tablename__ = "courses"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    teacher: Mapped[str] = mapped_column(String(64), default="")
    credits: Mapped[int] = mapped_column(Integer, default=0)
    semester: Mapped[str] = mapped_column(String(32), default="")
    # 开课院系（对应 /api/courses/departments 后台配置列表）
    department: Mapped[str] = mapped_column(String(64), default="", index=True)

    reviews: Mapped[list["CourseReview"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", lazy="selectin"
    )


class CourseReview(Base, PKMixin, TimestampMixin):
    """课程评价。"""

    __tablename__ = "course_reviews"

    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer, default=5)
    content: Mapped[str] = mapped_column(Text, default="")

    course: Mapped["Course"] = relationship(back_populates="reviews")

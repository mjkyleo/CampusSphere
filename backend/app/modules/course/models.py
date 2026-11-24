"""课程模块 ORM 模型。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text
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

    reviews: Mapped[list[CourseReview]] = relationship(
        # P2-17：不用模型级 selectin——列表/详情响应都不序列化评价，
        # eager 装载只会把全库评价拉进内存。删除课程时的级联清理由
        # flush 内的按需惰性加载完成（评价经 course_reviews.course_id
        # 的 DB 级 ON DELETE CASCADE 兜底）。
        back_populates="course", cascade="all, delete-orphan"
    )


class CourseReview(Base, PKMixin, TimestampMixin):
    """课程评价。

    P1-7：同一用户对同一课程仅允许一条评价。应用层 SELECT-then-INSERT
    拦不住并发双插（双击/脚本），此处以命名唯一索引兜底，service 层把
    IntegrityError 转 409。
    """

    __tablename__ = "course_reviews"
    __table_args__ = (
        Index("uq_course_review_user", "course_id", "user_id", unique=True),
    )

    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer, default=5)
    content: Mapped[str] = mapped_column(Text, default="")
    # "有用"点赞数（P2-22：此前仅前端 mock，落库需要真实列）
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)

    course: Mapped[Course] = relationship(back_populates="reviews")

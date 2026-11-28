"""兼职模块 ORM 模型。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import ApplicationStatus, JobStatus
from app.common.models import Base, PKMixin, TimestampMixin


class Job(Base, PKMixin, TimestampMixin):
    """兼职岗位。"""

    __tablename__ = "jobs"

    poster_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    company: Mapped[str] = mapped_column(String(128), default="")
    salary: Mapped[int] = mapped_column(Integer, default=0, comment="单位：分/天或月薪分")
    salary_type: Mapped[int] = mapped_column(Integer, default=1)  # 0 时薪 1 日薪 2 月薪 3 按次
    category: Mapped[str] = mapped_column(String(32), default="other")
    location: Mapped[str] = mapped_column(String(255), default="", server_default="")
    contact: Mapped[str] = mapped_column(String(255), default="", server_default="")
    requirements: Mapped[str] = mapped_column(Text, default="", server_default="")
    status: Mapped[int] = mapped_column(Integer, default=JobStatus.OPEN.value, index=True)

    applications: Mapped[list[JobApplication]] = relationship(
        back_populates="job", cascade="all, delete-orphan", lazy="selectin"
    )


class JobApplication(Base, PKMixin, TimestampMixin):
    """兼职申请。

    P2-3：同一申请人对同一岗位仅允许一条申请，命名唯一索引兜底并发双插
    （应用层 SELECT-then-INSERT 存在竞态窗口），service 层 IntegrityError → 409。
    """

    __tablename__ = "job_applications"
    __table_args__ = (
        Index("uq_job_application", "job_id", "applicant_id", unique=True),
    )

    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    applicant_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    status: Mapped[int] = mapped_column(Integer, default=ApplicationStatus.PENDING.value, index=True)
    note: Mapped[str] = mapped_column(Text, default="")

    job: Mapped[Job] = relationship(back_populates="applications")

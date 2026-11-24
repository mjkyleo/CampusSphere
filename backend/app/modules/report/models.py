"""举报模块 ORM 模型。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import ReportStatus
from app.common.models import Base, PKMixin, TimestampMixin


class Report(Base, PKMixin, TimestampMixin):
    """举报工单。

    P1-9：同一举报人对同一目标只允许一条工单（唯一索引兜底并发双插），
    service 层捕获 IntegrityError 转 409；自动封禁统计因此可以按
    distinct 举报人计数，不会被重复提交灌水。
    """

    __tablename__ = "reports"
    __table_args__ = (
        Index(
            "uq_report_reporter_target",
            "reporter_id", "target_type", "target_id",
            unique=True,
        ),
    )

    reporter_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(16), index=True)  # user/item/message/...
    target_id: Mapped[str] = mapped_column(String(36), index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[int] = mapped_column(Integer, default=ReportStatus.PENDING.value, index=True)
    handled_by: Mapped[str] = mapped_column(String(36), nullable=True, default=None)

    logs: Mapped[list[ReportLog]] = relationship(
        back_populates="report", cascade="all, delete-orphan", lazy="selectin"
    )


class ReportLog(Base, PKMixin, TimestampMixin):
    """举报处理日志。"""

    __tablename__ = "report_logs"

    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), index=True)
    operator_id: Mapped[str] = mapped_column(String(36), default="")
    action: Mapped[str] = mapped_column(String(32), default="")
    note: Mapped[str] = mapped_column(Text, default="")

    report: Mapped[Report] = relationship(back_populates="logs")

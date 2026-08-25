"""举报模块 ORM 模型。"""

from __future__ import annotations

from sqlalchemy import UUID, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import ReportStatus
from app.common.models import Base, PKMixin, TimestampMixin


class Report(Base, PKMixin, TimestampMixin):
    """举报工单。"""

    __tablename__ = "reports"

    reporter_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(16), index=True)  # user/item/message/...
    target_id: Mapped[str] = mapped_column(String(36), index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[int] = mapped_column(Integer, default=ReportStatus.PENDING.value, index=True)
    handled_by: Mapped[str] = mapped_column(String(36), nullable=True, default=None)

    logs: Mapped[list["ReportLog"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", lazy="selectin"
    )


class ReportLog(Base, PKMixin, TimestampMixin):
    """举报处理日志。"""

    __tablename__ = "report_logs"

    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), index=True)
    operator_id: Mapped[str] = mapped_column(String(36), default="")
    action: Mapped[str] = mapped_column(String(32), default="")
    note: Mapped[str] = mapped_column(Text, default="")

    report: Mapped["Report"] = relationship(back_populates="logs")

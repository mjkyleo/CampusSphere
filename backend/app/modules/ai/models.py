"""AI 模块 ORM 模型。

两张表都只服务于**可观测性**与**当日缓存**，不承担业务主流程，
因此即便写入失败也不允许影响 AI 响应（``service`` 中对落库做了 try/except 兜底）。
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, PKMixin, TimestampMixin


class AiGenerationLog(Base, PKMixin, TimestampMixin):
    """AI 调用日志：成本监控、降级率统计、面试可讲的"AI 可观测性"。"""

    __tablename__ = "ai_generation_log"

    user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    # greeting / item_description / course_summary / moderation / insights
    capability: Mapped[str] = mapped_column(String(32), index=True, default="")
    model: Mapped[str] = mapped_column(String(64), default="")
    # llm=真实模型 / fallback=模板降级 / rule=规则引擎
    source: Mapped[str] = mapped_column(String(16), default="llm")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    detail: Mapped[str] = mapped_column(String(255), default="")


class AiDailyGreeting(Base, PKMixin, TimestampMixin):
    """首页问候当日缓存。

    同一 (用户, 日期, 状态, 重点, 第几次) 复用同一条，避免"刷新就换一句"显得廉价；
    「换一句」通过 attempt+1 命中新行，从而拿到新的多样性手法。
    """

    __tablename__ = "ai_daily_greeting"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "day", "mood", "focus", "attempt", name="uq_ai_greeting_slot"
        ),
    )

    user_id: Mapped[str] = mapped_column(String(36), index=True)
    day: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    mood: Mapped[str] = mapped_column(String(16), default="")
    focus: Mapped[str] = mapped_column(String(16), default="")
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    period: Mapped[str] = mapped_column(String(16), default="")
    text: Mapped[str] = mapped_column(String(200), default="")
    emoji: Mapped[str] = mapped_column(String(8), default="")
    source: Mapped[str] = mapped_column(String(16), default="llm")

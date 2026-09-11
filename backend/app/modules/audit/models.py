"""审计日志 ORM 模型。

为什么独立建表，而不是只用 structlog
-----------------------------------
structlog 输出的是流式日志，适合排障与采集，但满足不了"运营可查"：
管理员想看"张三今天几点登录的"，不可能去 grep 几 GB 的日志文件。
审计日志因此独立建表，特点：

* **结构化可筛选**：按用户 / 动作 / 结果 / 时间范围过滤，直接支撑后台查询页；
* **独立事务提交**：业务失败（例如登录失败）恰恰是最该留痕的事件，
  而失败通常伴随回滚 —— 若与业务共用 session，日志会一起消失；
* **只追加不可改**：不继承 ``TimestampMixin``（避免 updated_at 语义），
  也不提供任何更新/删除接口，写入即定稿。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base, PKMixin


class AuditLog(Base, PKMixin):
    """用户 / 管理员关键操作留痕。"""

    __tablename__ = "audit_logs"

    # 审计场景下按时间倒序翻页是最高频操作，因此单独建索引。
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # ---- 操作主体 ----
    # actor_type: user（普通用户）/ admin（管理员）/ system / anonymous（未登录）
    actor_type: Mapped[str] = mapped_column(String(16), default="anonymous", index=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    # 主体快照（用户名/邮箱）：用户被删除后仍可追溯"谁干过什么"
    actor_label: Mapped[str] = mapped_column(String(128), default="")

    # ---- 动作与结果 ----
    # action 取值见 AuditAction；result: success / failure
    action: Mapped[str] = mapped_column(String(48), index=True)
    result: Mapped[str] = mapped_column(String(16), default="success", index=True)

    # ---- 操作对象（可选）----
    target_type: Mapped[str] = mapped_column(String(32), default="")
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # ---- 上下文 ----
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(512), default="")
    request_id: Mapped[str] = mapped_column(String(64), default="", index=True)

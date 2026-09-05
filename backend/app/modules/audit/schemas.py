"""审计日志 DTO。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogOut(BaseModel):
    """单条审计记录。

    额外附带 ``action_label`` / ``result_label`` / ``actor_type_label``
    三个中文字段，避免前端自己再维护一份动作字典（两处字典迟早会不同步）。
    """

    id: str
    created_at: datetime
    actor_type: str
    actor_id: str | None = None
    actor_label: str = ""
    action: str
    result: str = "success"
    target_type: str = ""
    target_id: str | None = None
    detail: dict = Field(default_factory=dict)
    ip: str = ""
    user_agent: str = ""
    request_id: str = ""

    action_label: str = ""
    result_label: str = ""
    actor_type_label: str = ""


class AuditLogPage(BaseModel):
    """分页结果。"""

    items: list[AuditLogOut] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0


class AuditActionOption(BaseModel):
    """动作下拉选项。"""

    value: str
    label: str

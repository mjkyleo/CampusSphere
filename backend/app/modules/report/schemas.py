"""举报模块 Pydantic 模型。"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# 举报目标类型收敛为封闭枚举（P1-9）：自由串会污染按 target_type 统计的
# 自动封禁口径，也便于前端下拉选项与后端校验取自同一集合。
# 取值与前端 types.ts 的 ReportTargetType 保持一致。
ReportTargetType = Literal["user", "item", "message", "comment", "share", "course", "stall"]


class ReportCreate(BaseModel):
    target_type: ReportTargetType = Field(description="user/item/message/comment/share/course/stall")
    target_id: str
    reason: str = Field(min_length=1, max_length=500)


class ReportHandle(BaseModel):
    action: str = Field(description="resolve/reject/ban")
    note: str = ""


class ReportLogOut(BaseModel):
    id: UUID
    operator_id: str
    action: str
    note: str

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: UUID
    reporter_id: str
    target_type: str
    target_id: str
    reason: str
    status: int
    handled_by: str | None = None
    logs: list[ReportLogOut] = []

    model_config = {"from_attributes": True}

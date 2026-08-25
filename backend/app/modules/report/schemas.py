"""举报模块 Pydantic 模型。"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.common.enums import ReportTargetType


class ReportCreate(BaseModel):
    target_type: str = Field(description="user/item/message/comment/share")
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
    handled_by: Optional[str] = None
    logs: List[ReportLogOut] = []

    model_config = {"from_attributes": True}

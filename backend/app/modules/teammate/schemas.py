"""队友招募 Pydantic 模型。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class TeamCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    required_roles: str = Field(default="", max_length=255)
    category: str = Field(default="", max_length=32)
    # P2-5：max_members 需为合理正数（service 层据此执行满员判断）
    max_members: int = Field(default=3, ge=1, le=100)
    contact_info: str = Field(default="", max_length=255)


class TeamUpdate(BaseModel):
    status: int | None = None


class TeamOut(BaseModel):
    id: UUID
    creator_id: str
    title: str
    description: str
    required_roles: str
    status: int
    category: str = "其他"
    max_members: int = 3
    contact_info: str = ""
    member_count: int = 0

    model_config = {"from_attributes": True}


class JoinRequest(BaseModel):
    role: str = Field(default="", max_length=64)


class TeamMemberOut(BaseModel):
    id: UUID
    team_id: str
    user_id: str
    role: str
    status: int

    model_config = {"from_attributes": True}

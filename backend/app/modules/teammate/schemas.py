"""队友招募 Pydantic 模型。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class TeamCreate(BaseModel):
    title: str
    description: str = ""
    required_roles: str = ""
    category: str = ""
    max_members: int = 3
    contact_info: str = ""


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
    role: str = ""


class TeamMemberOut(BaseModel):
    id: UUID
    team_id: str
    user_id: str
    role: str
    status: int

    model_config = {"from_attributes": True}

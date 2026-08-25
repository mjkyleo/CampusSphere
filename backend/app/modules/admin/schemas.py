"""管理后台 Pydantic 模型。"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AdminOut(BaseModel):
    id: UUID
    username: str
    role_id: Optional[str] = None
    disabled: bool = False
    permissions: List[str] = []

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str
    description: str = ""
    permissions: List[str] = []


class BanRequest(BaseModel):
    reason: str = ""


class EmailRegisterConfig(BaseModel):
    """邮箱注册规则（后台可动态配置，DB 值覆盖 school.yaml 默认值）。"""

    enabled: bool = True
    domains: List[str] = []
    pattern: str = ""


class ItemReviewConfig(BaseModel):
    """二手物品发布审核开关（DB 值覆盖 school.yaml 默认值）。"""

    enabled: bool = False


class ItemReviewRejectRequest(BaseModel):
    """拒绝审核时的原因说明。"""

    reason: str = ""

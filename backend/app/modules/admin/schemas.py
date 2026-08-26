"""管理后台 Pydantic 模型。"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminDiscoverRequest(BaseModel):
    """用网关密钥换取短时网关令牌。"""

    gateway_key: str


class AdminPromoteRequest(BaseModel):
    """将普通用户提升为管理员时设置其后台登录密码（必填）。"""

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


class ItemCategoriesConfig(BaseModel):
    """二手交易分类列表（后台可动态配置，DB 值覆盖 school.yaml 默认值）。"""

    categories: List[str] = []


class CourseDepartmentsConfig(BaseModel):
    """课程开课院系列表（后台可动态配置，DB 值覆盖 school.yaml 默认值）。"""

    departments: List[str] = []


class AiFeatureConfig(BaseModel):
    """AI 智能助手功能开关（DB 值覆盖 school.yaml 默认值）。

    个人开发者无大模型 API 额度时保持关闭，前端隐藏所有 AI 入口；
    额度到位后管理员在后台一键开启即可上线。
    """

    enabled: bool = False
    model: str = "gemini-2.0-flash"


class ItemReviewRejectRequest(BaseModel):
    """拒绝审核时的原因说明。"""

    reason: str = ""

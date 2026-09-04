"""管理后台 Pydantic 模型。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

# EmailRegisterConfig 为**有意的再导出**：admin.router 从本模块导入它，
# 而实现已上移到 app.common.schemas（auth 与 admin 共用，避免 auth 顶层依赖 admin）。
from app.common.schemas import EmailRegisterConfig  # noqa: F401


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
    role_id: str | None = None
    disabled: bool = False
    permissions: list[str] = []

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str
    description: str = ""
    permissions: list[str] = []


class BanRequest(BaseModel):
    reason: str = ""


class ItemReviewConfig(BaseModel):
    """二手物品发布审核开关（DB 值覆盖 school.yaml 默认值）。"""

    enabled: bool = False


class ItemCategoriesConfig(BaseModel):
    """二手交易分类列表（后台可动态配置，DB 值覆盖 school.yaml 默认值）。"""

    categories: list[str] = []


class CourseDepartmentsConfig(BaseModel):
    """课程开课院系列表（后台可动态配置，DB 值覆盖 school.yaml 默认值）。"""

    departments: list[str] = []


class JobCategoriesConfig(BaseModel):
    """兼职岗位分类列表（后台可动态配置，DB 值覆盖 school.yaml 默认值）。"""

    categories: list[str] = []


class ShareCategoriesConfig(BaseModel):
    """学术资料分类列表（后台可动态配置，DB 值覆盖 school.yaml 默认值）。"""

    categories: list[str] = []


class TeammateCategoriesConfig(BaseModel):
    """搭子组队分类列表（后台可动态配置，DB 值覆盖 school.yaml 默认值）。"""

    categories: list[str] = []


class DepartmentGroup(BaseModel):
    """一个学部及其下属院系。"""

    group: str
    departments: list[str] = []


class CourseDepartmentGroupsConfig(BaseModel):
    """课程院系按学部分组（后台可动态配置）。

    用于前端「学部 Tab → 院系 chips」两级筛选，避免 40+ 院系平铺溢出。
    """

    groups: list[DepartmentGroup] = []


class CanteenConfig(BaseModel):
    """食堂维度枚举配置（后台可动态配置）。

    ``zones`` 为「学部 → 餐饮区列表」映射；``semesters`` 为空表示不启用
    学期筛选，``current_semester`` 为空表示前端默认展示全部学期。
    """

    campuses: list[str] = []
    zones: dict[str, list[str]] = {}
    types: list[str] = []
    semesters: list[str] = []
    current_semester: str = ""


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

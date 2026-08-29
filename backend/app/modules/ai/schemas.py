"""AI 智能助手 Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AiFeatureConfig(BaseModel):
    """AI 智能助手功能开关（后台可动态配置，DB 值覆盖 school.yaml 默认值）。

    个人开发者模式下默认关闭：避免无大模型 API 额度时前端展示假数据，
    管理员可在后台一键开启/关闭，实现"功能先抽离、额度到位再上线"。
    """

    enabled: bool = False
    model: str = "gemini-2.0-flash"


class AiStatusOut(BaseModel):
    """AI 功能状态（公开端点，供前端决定是否渲染 AI 区块）。"""

    enabled: bool = False
    available: bool = False
    message: str = ""


class InsightRequest(BaseModel):
    """首页校园智能灵感。"""

    topic: str = Field(min_length=1, max_length=200)


class ItemDescriptionRequest(BaseModel):
    """闲置物品描述 AI 润色。"""

    title: str = Field(min_length=1, max_length=100)
    category: str = Field(max_length=50)


class CourseSummaryRequest(BaseModel):
    """课程评价 AI 汇总提炼。"""

    reviewTexts: list[str] = Field(min_length=1, max_length=50)


class CategorizeRequest(BaseModel):
    """内容自动分类与安全预审（发帖场景预留）。"""

    content: str = Field(min_length=1, max_length=5000)


class CategorizeOut(BaseModel):
    """内容分类结果。"""

    category: str
    isSafe: bool
    summary: str

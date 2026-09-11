"""AI 智能助手 Pydantic 模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AiFeatureConfig(BaseModel):
    """AI 智能助手功能开关（后台可动态配置，DB 值覆盖 school.yaml 默认值）。

    个人开发者模式下默认关闭：避免无大模型 API 额度时前端展示假数据，
    管理员可在后台一键开启/关闭，实现"功能先抽离、额度到位再上线"。
    """

    enabled: bool = False
    model: str = "deepseek-chat"


class AiCapabilityState(BaseModel):
    """单个 AI 能力的可用状态。

    ``available`` 决定是否渲染入口；``degraded`` 表示上游熔断中、当前走降级方案。
    """

    available: bool = False
    degraded: bool = False


class AiStatusOut(BaseModel):
    """AI 功能状态（公开端点，供前端按能力决定是否渲染 AI 区块）。"""

    enabled: bool = False
    available: bool = False
    provider: str = "openai_compatible"
    model: str = ""
    capabilities: dict[str, AiCapabilityState] = Field(default_factory=dict)
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
    """内容分类结果（``source`` 标明 llm / rule，便于前端与埋点区分）。"""

    category: str
    isSafe: bool
    summary: str
    source: str = "llm"


# ------------------------------------------------------------------
# 首页问候（微采集）
# ------------------------------------------------------------------

MOOD_KEYS = ("energetic", "steady", "tired", "sprint")
FOCUS_KEYS = ("study", "contest", "social", "relax")


class GreetingRequest(BaseModel):
    """首页每日问候请求。

    ``mood`` / ``focus`` 走白名单枚举（防 prompt 注入）；``clientSeed`` 由前端
    每次启动生成，用于让同一天不同次启动拿到不同句子。
    """

    mood: str = ""
    focus: str = ""
    clientSeed: str = Field(default="", max_length=64)
    regenerate: bool = False


class GreetingOut(BaseModel):
    """首页每日问候结果。

    ``source``：``llm`` 真实生成 / ``fallback`` 模板降级。前端据此决定是否展示
    「AI」角标——降级时正常渲染卡片，不报错、不阻塞。
    """

    text: str
    emoji: str = "✨"
    source: str = "llm"
    period: str = ""
    mood: str = ""
    focus: str = ""
    attempt: int = 0

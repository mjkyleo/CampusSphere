"""AI 智能助手路由：/api/ai/*。

- ``GET /api/ai/status`` 为公开端点（见 core.middleware.PUBLIC_PATHS），
  前端据此决定是否渲染 AI 相关 UI 区块；
- 其余生成类端点均需登录，且受管理后台功能开关控制：
  开关关闭时返回业务错误码（40300），前端不展示假数据；
- 全部生成类端点受**每用户每日配额**约束（P2-11）：单账号刷接口烧光
  Gemini 配额会拖垮全部用户的 AI 能力（429 后全员不可用）。
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import BizError, ErrorCode
from app.core.redis import redis_incr
from app.core.response import ApiResponse
from app.modules.ai.schemas import (
    AiStatusOut,
    CategorizeOut,
    CategorizeRequest,
    CourseSummaryRequest,
    InsightRequest,
    ItemDescriptionRequest,
)
from app.modules.ai.service import (
    categorize_content,
    generate_item_description,
    get_ai_status,
    smart_campus_insights,
    summarize_course_reviews,
)
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User

router = APIRouter(prefix="/api/ai", tags=["ai"])

# 每用户每日配额：school.yaml 的 ai.daily_limit_per_user 可覆盖，缺省 20 次
_AI_DAILY_LIMIT_DEFAULT = 20
_AI_QUOTA_PREFIX = "ai:quota:"


def _daily_limit() -> int:
    try:
        return max(1, int((settings.ai or {}).get("daily_limit_per_user", _AI_DAILY_LIMIT_DEFAULT)))
    except (TypeError, ValueError):
        return _AI_DAILY_LIMIT_DEFAULT


async def enforce_ai_quota(user: User = Depends(get_current_user)) -> User:
    """依赖工厂：每用户每日生成次数配额（自然日 Redis 计数，次日自动归零）。

    Redis 不可用时计数失败放行（与全局限流同一 fail-open 策略）。
    """
    day = datetime.now(UTC).strftime("%Y%m%d")
    key = f"{_AI_QUOTA_PREFIX}{user.id}:{day}"
    count = await redis_incr(key, ttl=86400 + 3600)
    if count and count > _daily_limit():
        raise BizError(ErrorCode.TOO_MANY_REQUESTS, "今日 AI 使用次数已达上限，请明日再试")
    return user


@router.get("/status", response_model=ApiResponse[AiStatusOut])
async def ai_status(db: AsyncSession = Depends(get_db)):
    """AI 功能开关状态（公开）：前端据此条件渲染 AI 入口。"""
    return ApiResponse.ok(data=AiStatusOut(**await get_ai_status(db)))


@router.post("/insights", response_model=ApiResponse[dict])
async def insights(
    data: InsightRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(enforce_ai_quota),
):
    """首页校园智能灵感。"""
    text = await smart_campus_insights(db, data.topic)
    return ApiResponse.ok(data={"text": text})


@router.post("/item-description", response_model=ApiResponse[dict])
async def item_description(
    data: ItemDescriptionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(enforce_ai_quota),
):
    """闲置发布描述 AI 润色。"""
    text = await generate_item_description(db, data.title, data.category)
    return ApiResponse.ok(data={"text": text})


@router.post("/course-summary", response_model=ApiResponse[dict])
async def course_summary(
    data: CourseSummaryRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(enforce_ai_quota),
):
    """课程评价 AI 汇总。"""
    text = await summarize_course_reviews(db, data.reviewTexts)
    return ApiResponse.ok(data={"text": text})


@router.post("/categorize", response_model=ApiResponse[CategorizeOut])
async def categorize(
    data: CategorizeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(enforce_ai_quota),
):
    """内容自动分类与安全预审（发帖场景预留）。"""
    result = await categorize_content(db, data.content)
    return ApiResponse.ok(data=CategorizeOut(**result))

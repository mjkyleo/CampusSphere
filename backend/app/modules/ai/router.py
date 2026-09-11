"""AI 智能助手路由：/api/ai/*。

- ``GET /api/ai/status`` 为公开端点（见 core.middleware.PUBLIC_PATHS），
  返回**能力级**可用状态，前端据此按能力决定是否渲染 AI 区块；
- 生成类端点均需登录，且受管理后台开关 + 能力开关控制；
- ``/api/ai/greeting`` 为唯一可降级端点：无 Key / 上游故障时返回模板
  （``source="fallback"``），保证首页永不因 AI 而阻塞。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.ai.schemas import (
    AiStatusOut,
    CategorizeOut,
    CategorizeRequest,
    CourseSummaryRequest,
    GreetingOut,
    GreetingRequest,
    InsightRequest,
    ItemDescriptionRequest,
)
from app.modules.ai.service import (
    categorize_content,
    generate_greeting,
    generate_item_description,
    get_ai_status,
    smart_campus_insights,
    summarize_course_reviews,
)
from app.modules.auth.deps import get_current_user

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status", response_model=ApiResponse[AiStatusOut])
async def ai_status(db: AsyncSession = Depends(get_db)):
    """AI 功能开关状态（公开）：前端据此条件渲染 AI 入口。"""
    return ApiResponse.ok(data=AiStatusOut(**await get_ai_status(db)))


@router.post("/greeting", response_model=ApiResponse[GreetingOut])
async def greeting(
    data: GreetingRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """首页每日问候（微采集）。永不抛错：异常一律降级为模板文案。"""
    result = await generate_greeting(
        db,
        user_id=str(user.id),
        mood=data.mood,
        focus=data.focus,
        client_seed=data.clientSeed,
        regenerate=data.regenerate,
    )
    return ApiResponse.ok(data=GreetingOut(**result))


@router.post("/insights", response_model=ApiResponse[dict])
async def insights(
    data: InsightRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """首页校园智能灵感。"""
    text = await smart_campus_insights(db, data.topic)
    return ApiResponse.ok(data={"text": text})


@router.post("/item-description", response_model=ApiResponse[dict])
async def item_description(
    data: ItemDescriptionRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """闲置发布描述 AI 润色。"""
    text = await generate_item_description(db, data.title, data.category)
    return ApiResponse.ok(data={"text": text})


@router.post("/course-summary", response_model=ApiResponse[dict])
async def course_summary(
    data: CourseSummaryRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """课程评价 AI 汇总。"""
    text = await summarize_course_reviews(db, data.reviewTexts)
    return ApiResponse.ok(data={"text": text})


@router.post("/categorize", response_model=ApiResponse[CategorizeOut])
async def categorize(
    data: CategorizeRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """内容自动分类与安全预审（LLM 不可用时降级为规则引擎）。"""
    result = await categorize_content(db, data.content)
    return ApiResponse.ok(data=CategorizeOut(**result))

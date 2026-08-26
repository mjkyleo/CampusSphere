"""AI 智能助手路由：/api/ai/*。

- ``GET /api/ai/status`` 为公开端点（见 core.middleware.PUBLIC_PATHS），
  前端据此决定是否渲染 AI 相关 UI 区块；
- 其余生成类端点均需登录，且受管理后台功能开关控制：
  开关关闭时返回业务错误码（40300），前端不展示假数据。
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

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status", response_model=ApiResponse[AiStatusOut])
async def ai_status(db: AsyncSession = Depends(get_db)):
    """AI 功能开关状态（公开）：前端据此条件渲染 AI 入口。"""
    return ApiResponse.ok(data=AiStatusOut(**await get_ai_status(db)))


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
    """内容自动分类与安全预审（发帖场景预留）。"""
    result = await categorize_content(db, data.content)
    return ApiResponse.ok(data=CategorizeOut(**result))

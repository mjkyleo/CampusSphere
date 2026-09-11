"""健康检查与指标路由。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.logging import get_logger
from app.modules.launcher.metrics import get_metrics, metrics_content_type

_logger = get_logger("launcher.router")
router = APIRouter(tags=["launcher"])


@router.get("/health")
@router.get("/api/health")
async def health() -> dict:
    """健康检查：返回服务与基础依赖状态。

    同时挂在 /health 与 /api/health 两个路径上。
    后者不是冗余：前端 dev server（frontend/server.ts）本地实现了
    ``/api/health`` 并直接返回 200，而生产由 nginx 统一转发 /api/* 到后端 ——
    若后端不提供该路径，同一个探测就会在开发环境 200、上线后 404。
    e2e 的 webServer 健康检查用的正是 ``${BACKEND_URL}/api/health``。
    """
    status = "ok"
    db_ok = True
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
        status = "degraded"
    return {
        "status": status,
        "service": settings.app_name,
        "school": settings.school_name,
        "database": "up" if db_ok else "down",
    }


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus 指标端点。"""
    return PlainTextResponse(get_metrics(), media_type=metrics_content_type())

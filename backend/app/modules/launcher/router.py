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
async def health() -> dict:
    """健康检查：返回服务与基础依赖状态。"""
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

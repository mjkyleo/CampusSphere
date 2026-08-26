"""应用工厂：装配路由、中间件、异常处理、WebSocket 与生命周期。"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import SessionLocal, engine, init_models
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import GatewayMiddleware
from app.modules.admin.router import router as admin_router
from app.modules.ai.router import router as ai_router
from app.modules.auth.router import router as auth_router
from app.modules.canteen.router import router as canteen_router
from app.modules.course.router import router as course_router
from app.modules.item.router import router as item_router
from app.modules.job.router import router as job_router
from app.modules.launcher.otel import init_otel
from app.modules.launcher.router import router as launcher_router
from app.modules.message.router import router as message_router
from app.modules.message.ws import manager, websocket_endpoint
from app.modules.report.router import router as report_router
from app.modules.share.router import router as share_router
from app.modules.storage.router import router as storage_router
from app.modules.teammate.router import router as teammate_router
from app.modules.user.router import router as user_router

_logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    _logger.info("app_starting", school=settings.school_name)
    # 开发模式（SQLite）自动建表，免去手动 alembic
    if settings.db_url.startswith("sqlite"):
        from app.common.models import Base

        await init_models(Base)
    # 初始化后台管理员
    async with SessionLocal() as db:
        from app.modules.admin.service import ensure_seed

        try:
            await ensure_seed(db)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("admin_seed_failed", error=str(exc))
    # 启动 WebSocket Redis 广播监听
    try:
        await manager.start_listener()
    except Exception:  # noqa: BLE001
        pass
    yield
    await engine.dispose()
    _logger.info("app_shutdown")


def create_app() -> FastAPI:
    """创建并装配 FastAPI 应用。"""
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="校园生活平台（Python 重写）模块化单体后端",
        lifespan=lifespan,
    )

    # 统一异常处理
    register_exception_handlers(app)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 网关中间件（鉴权/限流/请求ID）
    app.add_middleware(GatewayMiddleware, rate_limit_per_minute=settings.rate_limit_per_minute)

    # 业务路由
    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(item_router)
    app.include_router(message_router)
    app.include_router(course_router)
    app.include_router(canteen_router)
    app.include_router(job_router)
    app.include_router(share_router)
    app.include_router(teammate_router)
    app.include_router(report_router)
    app.include_router(admin_router)
    app.include_router(ai_router)
    app.include_router(storage_router)
    app.include_router(launcher_router)

    # WebSocket
    app.add_api_websocket_route("/ws", websocket_endpoint)

    # OpenTelemetry
    init_otel(app, service_name=settings.app_name)

    @app.get("/")
    async def root() -> dict:
        return {"service": settings.app_name, "school": settings.school_name, "docs": "/docs"}

    return app


app = create_app()

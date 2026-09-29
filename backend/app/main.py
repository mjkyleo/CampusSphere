"""应用工厂：装配路由、中间件、异常处理、WebSocket 与生命周期。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.config_reload import start_config_reloader, stop_config_reloader
from app.core.database import SessionLocal, engine, init_models
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import GatewayMiddleware
from app.core.redis import close_redis
from app.modules.admin.router import router as admin_router
from app.modules.ai.router import router as ai_router
from app.modules.audit.router import router as audit_router
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
    # 启动逻辑一并放进 try：启动中途失败（如 init_models 异常）也会走 finally 释放，
    # 避免"半启动"状态下残留已申请的连接与后台任务。
    try:
        configure_logging()
        # 启动期管理员安全校验：生产环境（非 debug 且 admin_gateway_enforce）若网关密钥或 bootstrap
        # 密码过弱/缺失，直接 SystemExit 拒绝带病上线（开发/测试放宽模式跳过）。
        from app.core.config import validate_admin_security

        validate_admin_security()
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
            except Exception as exc:
                _logger.warning("admin_seed_failed", error=str(exc))
        # 启动 WebSocket Redis 广播监听
        try:
            await manager.start_listener()
        except Exception:
            pass
        # 启动配置热更新监听（Redis 不可用时内部优雅降级，不影响启动）
        await start_config_reloader()
        # 预热对象存储连接（未配置 MinIO 时为空操作）：避免首个上传/签名请求
        # 在事件循环上付出同步建连（bucket_exists）的阻塞
        from app.core.storage import storage_client

        try:
            await storage_client.warmup()
        except Exception as exc:
            _logger.warning("storage_warmup_failed", error=str(exc))
        yield
    finally:
        # 关闭期资源释放顺序：后台任务 → 外部连接 → 数据库连接池。
        # 用 finally 保证运行期异常（或启动中途失败）时同样释放，避免句柄泄漏。
        try:
            await manager.stop_listener()
        except Exception as exc:
            _logger.warning("ws_listener_stop_failed", error=str(exc))
        try:
            await stop_config_reloader()
        except Exception as exc:
            _logger.warning("config_reloader_stop_failed", error=str(exc))
        try:
            await close_redis()
        except Exception as exc:
            _logger.warning("redis_close_failed", error=str(exc))
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

    # 中间件顺序（P2-7）：Starlette 后添加者在**外侧**。
    # 此前 CORS 在内、网关在外——预检 OPTIONS 与网关 401/429 响应都到不了
    # CORS 层，丢失 CORS 头，跨端写请求全部失败（同源部署掩盖了问题）。
    # 现为：网关（最内）→ 安全响应头 → CORS（最外），保证网关错误响应
    # 也携带 CORS 头与安全头。
    app.add_middleware(
        GatewayMiddleware,
        rate_limit_per_minute=settings.rate_limit_per_minute,
        auth_rate_limit_per_minute=settings.auth_rate_limit_per_minute,
    )

    from app.core.middleware import SecurityHeadersMiddleware

    app.add_middleware(SecurityHeadersMiddleware)

    # CORS：生产应显式白名单，避免 credentials=True 时放行任意源/方法/头。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Admin-Gateway"],
    )

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
    app.include_router(audit_router)
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

"""异步数据库引擎、会话工厂与 FastAPI 依赖。

开发/测试使用 ``sqlite+aiosqlite`` 零依赖启动；生产替换为 ``postgresql+asyncpg``。
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger("core.database")

# 创建异步引擎；SQLite 下禁用 pool_pre_ping（不支持）
_connect_args: dict = {}
if settings.db_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
else:
    _connect_args = {"pool_pre_ping": True}

engine = create_async_engine(
    settings.db_url,
    echo=settings.debug,
    future=True,
    connect_args=_connect_args,
)

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：提供请求级异步会话。"""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_models(base: type[DeclarativeBase]) -> None:
    """在开发模式下按需建表（等价于 alembic upgrade head）。"""
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
    _logger.info("db_models_initialized")

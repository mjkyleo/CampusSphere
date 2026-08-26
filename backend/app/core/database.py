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


# SQLite 轻量迁移：create_all 不会给已存在的表补列，这里对已知表执行 ALTER。
# key 为表名，value 为 (列名, 列 DDL) 列表。
_SQLITE_COLUMN_MIGRATIONS: dict[str, list[tuple[str, str]]] = {
    "user_profiles": [
        ("campus", "VARCHAR(64) DEFAULT ''"),
        ("contact_wx", "VARCHAR(64) DEFAULT ''"),
    ],
    "users": [
        ("is_admin", "BOOLEAN DEFAULT 0"),
    ],
    "courses": [
        ("department", "VARCHAR(64) DEFAULT ''"),
    ],
    "canteens": [
        ("image", "VARCHAR(512) DEFAULT ''"),
    ],
    "stalls": [
        ("image", "VARCHAR(512) DEFAULT ''"),
    ],
    "dishes": [
        ("image", "VARCHAR(512) DEFAULT ''"),
    ],
}


async def _run_sqlite_column_migrations(conn) -> None:
    """为 SQLite 已存在的表补充新列（幂等：已存在的列跳过）。"""
    for table, cols in _SQLITE_COLUMN_MIGRATIONS.items():
        try:
            result = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
            existing = {row[1] for row in result.fetchall()}
        except Exception:  # noqa: BLE001 - 表不存在则跳过
            continue
        for col, ddl in cols:
            if col not in existing:
                await conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                _logger.info("db_column_migrated", table=table, column=col)


async def init_models(base: type[DeclarativeBase]) -> None:
    """在开发模式下按需建表（等价于 alembic upgrade head）。"""
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
        if settings.db_url.startswith("sqlite"):
            await _run_sqlite_column_migrations(conn)
    _logger.info("db_models_initialized")

"""异步数据库引擎、会话工厂与 FastAPI 依赖。

开发/测试使用 ``sqlite+aiosqlite`` 零依赖启动；生产替换为 ``postgresql+asyncpg``。
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import get_logger, get_trace_id

_logger = get_logger("core.database")

# 创建异步引擎。
# - SQLite 无连接池概念，仅设 check_same_thread=False（线程安全检查放宽）。
# - PostgreSQL/MySQL 等启用连接池调优 + pool_pre_ping，避免连接耗尽与静默断连。
_connect_args: dict = {}
if settings.db_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
    engine = create_async_engine(
        settings.db_url,
        echo=settings.debug,
        future=True,
        connect_args=_connect_args,
    )
else:
    engine = create_async_engine(
        settings.db_url,
        echo=settings.debug,
        future=True,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
        pool_timeout=settings.db_pool_timeout,
    )

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# 全链路染色：把 trace id 以 SQL 注释形式注入每条语句
# ---------------------------------------------------------------------------
# 价值：慢 SQL 日志 / PG 的 pg_stat_statements / 云厂商 SQL 洞察里出现的
# 每一条语句都自带请求 ID，从而把「Nginx 访问日志 → 业务日志 → 慢 SQL」
# 三者串成一条线。排查时不再需要靠时间戳去猜哪条 SQL 属于哪个请求。
#
# 为何用注释而非独立列：注释对数据库是透明的（不改写语义、不影响执行计划），
# 却能原样出现在慢查询日志里 —— 这是唯一能穿透到 DB 侧的载体。
# 用 dialect 级 ``do_execute`` **接管执行**来注入注释，而不是用
# ``before_cursor_execute`` 的返回值改写语句 —— 后者在 SQLAlchemy 2.0.30
# **不生效**（实测：监听器确实被调用、也返回了改写后的语句，但数据库执行的
# 仍是原语句；Core select 与 text() 两条路径、Engine/Connection 实例级与
# 类级四种注册方式均如此）。因此这里改为由监听器自己执行改写后的语句，
# 并返回 True 告知 SQLAlchemy "已处理，无需再执行"。
#
# 为何用注释载体：注释对数据库透明（不改变语义与执行计划），却能原样出现在
# 慢查询日志 / pg_stat_statements / 云厂商 SQL 洞察里 —— 这是唯一能把
# trace id 穿透到 DB 侧的载体。
def _commented(statement: str) -> str | None:
    """给 SQL 加上 trace 注释；无 trace id 时返回 None（走默认路径）。"""
    trace_id = get_trace_id()
    if not trace_id:
        return None
    return f"/* trace_id={trace_id} */ {statement}"


@event.listens_for(engine.sync_engine, "do_execute")
def _do_execute_with_trace(cursor, statement, parameters, context):
    """带 trace 注释地执行 SQL。返回 True 表示已接管执行。"""
    commented = _commented(statement)
    if commented is None:
        return False  # 无请求上下文（后台任务/lifespan）→ 交回默认路径
    cursor.execute(commented, parameters)
    return True


@event.listens_for(engine.sync_engine, "do_execute_no_params")
def _do_execute_no_params_with_trace(cursor, statement, context):
    """无参 SQL（如 DDL）的注释注入。"""
    commented = _commented(statement)
    if commented is None:
        return False
    cursor.execute(commented)
    return True


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
    # 搭子组队：分类改为后台配置驱动后需要落库（原为前端写死常量）
    "teams": [
        ("category", "VARCHAR(32) DEFAULT '其他'"),
        ("max_members", "INTEGER DEFAULT 3"),
        ("contact_info", "VARCHAR(255) DEFAULT ''"),
    ],
    # 食堂按武大实际结构扩维：学部 / 餐饮区 / 类型 / 楼层 / 描述 / 标签 / 学期
    "canteens": [
        ("campus", "VARCHAR(32) DEFAULT ''"),
        ("zone", "VARCHAR(32) DEFAULT ''"),
        ("canteen_type", "VARCHAR(32) DEFAULT ''"),
        ("floor", "VARCHAR(32) DEFAULT ''"),
        ("description", "TEXT DEFAULT ''"),
        ("features", "TEXT DEFAULT '[]'"),
        ("popular_dishes", "TEXT DEFAULT '[]'"),
        ("opening_hours", "VARCHAR(64) DEFAULT ''"),
        ("semester", "VARCHAR(32) DEFAULT ''"),
    ],
}


# SQLite 轻量索引迁移：create_all 只会给**新建**的表建索引，已存在的表不会补。
# 部分唯一索引是并发安全的最后一道兜底（见 item.models.TradeSession），
# 老库升级时若缺失，就只能靠应用层的条件 UPDATE 单防，故必须在此补齐。
# value 为 (索引名, CREATE 语句) 列表；幂等：已存在同名索引则跳过。
_SQLITE_INDEX_MIGRATIONS: dict[str, list[tuple[str, str]]] = {
    "trade_sessions": [
        (
            "uq_trade_session_active_item",
            "CREATE UNIQUE INDEX uq_trade_session_active_item "
            "ON trade_sessions (item_id) WHERE status IN (0, 1)",
        ),
    ],
}


async def _run_sqlite_column_migrations(conn) -> None:
    """为 SQLite 已存在的表补充新列（幂等：已存在的列跳过）。"""
    for table, cols in _SQLITE_COLUMN_MIGRATIONS.items():
        try:
            result = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
            existing = {row[1] for row in result.fetchall()}
        except Exception:
            continue
        for col, ddl in cols:
            if col not in existing:
                await conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                _logger.info("db_column_migrated", table=table, column=col)

    for table, indexes in _SQLITE_INDEX_MIGRATIONS.items():
        try:
            result = await conn.exec_driver_sql(f"PRAGMA index_list({table})")
            existing = {row[1] for row in result.fetchall()}
        except Exception:
            continue
        for name, ddl in indexes:
            if name in existing:
                continue
            try:
                await conn.exec_driver_sql(ddl)
                _logger.info("db_index_migrated", table=table, index=name)
            except Exception:
                # 老数据里已存在重复活跃会话时，唯一索引会建不起来。
                # 记日志让运维知晓并可手工清理，但**不阻断启动**——
                # 否则一处脏数据会让整站起不来，代价远大于索引缺失。
                _logger.error("db_index_migration_failed", table=table, index=name)


async def init_models(base: type[DeclarativeBase]) -> None:
    """在开发模式下按需建表（等价于 alembic upgrade head）。"""
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
        if settings.db_url.startswith("sqlite"):
            await _run_sqlite_column_migrations(conn)
    _logger.info("db_models_initialized")

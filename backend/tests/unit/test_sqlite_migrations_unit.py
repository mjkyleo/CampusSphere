"""SQLite 轻量迁移的防回归测试。

历史缺陷：``_SQLITE_COLUMN_MIGRATIONS`` 曾是 dict 字面量且 ``"canteens"``
键写了两次，Python 保留后值导致 ``image`` 列的迁移被**静默丢弃** ——
老库升级后查询 ``Canteen.image`` 直接报 no such column。结构改为列表
（允许同表多条、按序幂等执行）后，本测试用「缺列老表」锁死补列链路。
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import _run_sqlite_column_migrations


@pytest.mark.asyncio
async def test_missing_canteen_image_column_is_added():
    """老库 canteens 表缺 image 列时，迁移必须补上（曾被键重复吞掉）。"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.exec_driver_sql(
                "CREATE TABLE canteens (id VARCHAR(36) PRIMARY KEY, name VARCHAR(64))"
            )
            await _run_sqlite_column_migrations(conn)
            rows = (await conn.exec_driver_sql("PRAGMA table_info(canteens)")).fetchall()
            cols = {row[1] for row in rows}
        assert "image" in cols  # 曾被字典键重复覆盖的迁移
        assert "campus" in cols  # 同表第二条迁移条目（扩维列）
        assert "semester" in cols
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_migration_skips_missing_tables():
    """迁移清单里的其他表不存在时不应抛异常（幂等 + 缺表跳过）。"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            # 不建任何表，直接跑迁移 —— 应安静通过
            await _run_sqlite_column_migrations(conn)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_column_migration_is_idempotent():
    """重复执行迁移不应报错（已存在的列跳过）。"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.exec_driver_sql(
                "CREATE TABLE canteens (id VARCHAR(36) PRIMARY KEY, name VARCHAR(64))"
            )
            await _run_sqlite_column_migrations(conn)
            await _run_sqlite_column_migrations(conn)  # 第二遍：全部跳过
            rows = (await conn.exec_driver_sql("PRAGMA table_info(canteens)")).fetchall()
            # 每列只出现一次
            assert len(rows) == len({row[1] for row in rows})
    finally:
        await engine.dispose()

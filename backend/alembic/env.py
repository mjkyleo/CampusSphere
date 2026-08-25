"""Alembic 环境（异步引擎）。

- 接入 app.common.models.Base.metadata（自动收集所有已注册模型）
- 通过 connection.run_sync 以同步方式执行迁移，兼容 SQLite 与 PostgreSQL
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.common.models import Base
from app.core.config import settings

# 导入所有模型模块，确保 Base.metadata 收集完整
from app.modules.auth import models as auth_models  # noqa: F401
from app.modules.user import models as user_models  # noqa: F401
from app.modules.item import models as item_models  # noqa: F401
from app.modules.message import models as message_models  # noqa: F401
from app.modules.course import models as course_models  # noqa: F401
from app.modules.canteen import models as canteen_models  # noqa: F401
from app.modules.job import models as job_models  # noqa: F401
from app.modules.share import models as share_models  # noqa: F401
from app.modules.teammate import models as teammate_models  # noqa: F401
from app.modules.report import models as report_models  # noqa: F401
from app.modules.admin import models as admin_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.db_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        {"sqlalchemy.url": settings.db_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

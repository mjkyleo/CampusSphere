"""Celery worker 使用的同步数据库访问层。

Web 进程使用异步引擎（sqlite+aiosqlite），而 Celery worker 是独立进程、
任务为同步函数，无法复用异步 Session。这里提供等价的同步 Engine / Session，
指向同一个数据库 URL（自动把 aiosqlite 异步驱动替换为内置 sqlite 驱动）。
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger("core.sync_db")

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _sync_url(url: str) -> str:
    """把 aiosqlite / asyncpg 等异步驱动替换为等价的同步驱动。

    生产环境（PostgreSQL）下 Celery worker 需用 psycopg2 同步驱动，
    否则 create_engine 拿到 asyncpg（异步驱动）会直接失败。
    """
    url = url.replace("sqlite+aiosqlite", "sqlite", 1)
    url = url.replace("postgresql+asyncpg", "postgresql+psycopg2", 1)
    return url


def get_engine() -> Engine:
    """懒加载创建同步 Engine（worker 进程内单例）。"""
    global _engine
    if _engine is None:
        sync_url = _sync_url(settings.db_url)
        _engine = create_engine(sync_url, pool_pre_ping=True)
        _logger.info("sync engine created: %s", sync_url)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """懒加载创建同步 sessionmaker（worker 进程内单例）。"""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory

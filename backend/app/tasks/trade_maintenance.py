"""二手交易维护任务：预占超时释放 + 状态一致性对账。

由 Celery Beat 周期触发（见 celery_app.py 的 beat_schedule）。任务为同步函数，
内部用 asyncio.run 驱动服务层的异步实现，避免与 item.service 重复一套 SQL。
"""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

_logger = get_logger("tasks.trade_maintenance")


def _run_async(coro) -> dict:
    """在同步 Celery worker 中执行异步协程。"""
    return asyncio.run(coro)


@celery_app.task(name="app.tasks.trade_maintenance.expire_stale_trades", bind=True)
def expire_stale_trades(self) -> dict:
    """释放超时未确认的 RESERVED 预占。"""
    from app.modules.item.service import expire_stale_trades as _impl

    engine = create_async_engine(settings.db_url, future=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _runner() -> dict:
        async with factory() as session:
            return await _impl(session)

    try:
        result = _run_async(_runner())
        _logger.info("trade_expire_task_done", result=result)
        return result
    except Exception as exc:  # pragma: no cover - worker 端重试由 Celery 处理
        _logger.error("trade_expire_task_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60) from exc
    finally:
        _run_async(engine.dispose())


@celery_app.task(name="app.tasks.trade_maintenance.reconcile_trade_states", bind=True)
def reconcile_trade_states(self) -> dict:
    """扫描并修复物品/会话状态错位。"""
    from app.modules.item.service import reconcile_trade_states as _impl

    engine = create_async_engine(settings.db_url, future=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _runner() -> dict:
        async with factory() as session:
            return await _impl(session)

    try:
        result = _run_async(_runner())
        _logger.info("trade_reconcile_task_done", result=result)
        return result
    except Exception as exc:  # pragma: no cover
        _logger.error("trade_reconcile_task_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60) from exc
    finally:
        _run_async(engine.dispose())

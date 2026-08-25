"""交易会话摘要生成任务（Celery 任务示例）。

异步从数据库读取交易会话信息，聚合为摘要 JSON 并写入 Redis 缓存（默认
15 分钟 TTL），供前端交易详情页直接读取，避免每次请求重复聚合查询。

触发示例（Python 解释器 / Web 层）::

    from app.tasks.summary import generate_trade_summary
    generate_trade_summary.delay(trade_id="8f14e45f-....")

也可在 worker 内用 ``celery -A app.tasks.celery_app:celery_app call`` 触发。
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select

from app.core.logging import get_logger
from app.core.redis import redis_get, redis_set
from app.core.sync_db import get_session_factory
from app.modules.auth.models import User
from app.modules.item.models import Item, TradeSession
from app.modules.message.models import Message
from app.tasks.celery_app import celery_app

_logger = get_logger("tasks.summary")

CACHE_PREFIX = "trade:summary:"
CACHE_TTL_SECONDS = 15 * 60  # 15 分钟


def _run(coro):
    """在同步 Celery 任务中执行异步 Redis 调用（worker 进程无运行中的事件循环）。"""
    return asyncio.run(coro)


@celery_app.task(name="app.tasks.summary.generate_trade_summary")
def generate_trade_summary(trade_id: str, force: bool = False) -> dict[str, Any]:
    """生成交易会话摘要并写入 Redis 缓存。

    :param trade_id: 交易会话 ID
    :param force: 为 True 时强制重新生成，忽略已有缓存
    :return: 摘要字典（同时写入 Redis 缓存）
    """
    cache_key = f"{CACHE_PREFIX}{trade_id}"

    if not force:
        cached = _run(redis_get(cache_key))
        if cached:
            try:
                return json.loads(cached)
            except (TypeError, json.JSONDecodeError):
                _logger.warning("缓存内容非法，重新生成: %s", cache_key)

    summary = _build_summary(trade_id)
    try:
        _run(redis_set(cache_key, json.dumps(summary, ensure_ascii=False), ttl=CACHE_TTL_SECONDS))
    except Exception as exc:  # noqa: BLE001 - 缓存失败不应影响主流程
        _logger.warning("写入摘要缓存失败（忽略）: %s", exc)

    _logger.info("交易会话摘要已生成: trade_id=%s cache_key=%s", trade_id, cache_key)
    return summary


def _build_summary(trade_id: str) -> dict[str, Any]:
    """从数据库聚合交易会话摘要（同步访问，供 Celery worker 使用）。"""
    session_factory = get_session_factory()
    with session_factory() as db:
        trade = db.get(TradeSession, trade_id)
        if trade is None:
            raise ValueError(f"交易会话不存在: {trade_id}")

        item = db.get(Item, trade.item_id)
        seller = db.get(User, trade.seller_id)
        buyer = db.get(User, trade.buyer_id)
        msg_count = (
            db.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.conversation_id == trade.conversation_id)
            )
            if trade.conversation_id
            else 0
        )

    return {
        "trade_id": str(trade.id),
        "item_id": str(trade.item_id),
        "item_title": item.title if item else None,
        "price": item.price if item else None,  # 单位：分
        "status": trade.status,
        "seller_id": str(trade.seller_id),
        "seller_nickname": seller.nickname if seller else None,
        "buyer_id": str(trade.buyer_id),
        "buyer_nickname": buyer.nickname if buyer else None,
        "conversation_id": str(trade.conversation_id) if trade.conversation_id else None,
        "message_count": msg_count or 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

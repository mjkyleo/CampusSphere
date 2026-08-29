"""Redis 连接池与客户端管理。

Redis 同时承担：热点缓存、限流计数、JWT 黑名单、WS 广播 Pub/Sub、Celery broker。
未连接时提供安全降级（内存兜底），保证无 Redis 也能本地开发/测试。
"""

from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger("core.redis")

_redis_pool: aioredis.Redis | None = None
# 无 Redis 时的内存兜底
_memory_fallback: dict = {}


async def get_redis() -> aioredis.Redis | None:
    """返回全局 Redis 客户端（懒连接）；不可用时返回 None。"""
    global _redis_pool
    if _redis_pool is not None:
        return _redis_pool
    try:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=0.5,
        )
        await _redis_pool.ping()
        _logger.info("redis_connected", url=settings.redis_url)
        return _redis_pool
    except Exception as exc:
        _logger.warning("redis_unavailable_fallback_memory", error=str(exc))
        _redis_pool = None
        return None


async def close_redis() -> None:
    """关闭全局 Redis 客户端并释放连接池与内存兜底（应用关闭期调用）。

    幂等：重复调用安全。先摘掉全局句柄再关闭，避免关闭期间新请求复用到
    正在关闭的连接。优先使用 redis-py 5.x 的 ``aclose()``，旧版本回退 ``close()``。
    """
    global _redis_pool
    client, _redis_pool = _redis_pool, None
    _memory_fallback.clear()
    if client is None:
        return
    try:
        aclose = getattr(client, "aclose", None)
        if aclose is not None:
            await aclose()
        else:  # pragma: no cover - redis<5 兼容分支
            await client.close()
        _logger.info("redis_closed")
    except Exception as exc:
        _logger.warning("redis_close_failed", error=str(exc))


async def redis_set(key: str, value: str, ttl: int | None = None) -> None:
    """写入键值，支持 TTL（秒）。"""
    client = await get_redis()
    if client is not None:
        await client.set(key, value, ex=ttl)
    else:
        _memory_fallback[key] = value


async def redis_get(key: str) -> str | None:
    """读取键值。"""
    client = await get_redis()
    if client is not None:
        return await client.get(key)
    return _memory_fallback.get(key)


async def redis_delete(key: str) -> None:
    """删除键。"""
    client = await get_redis()
    if client is not None:
        await client.delete(key)
    else:
        _memory_fallback.pop(key, None)


async def redis_publish(channel: str, message: str) -> int:
    """发布消息到频道，返回接收者数量。"""
    client = await get_redis()
    if client is not None:
        return await client.publish(channel, message)
    return 0


async def redis_subscribe(channel: str):
    """订阅频道，返回 pubsub 对象（无 Redis 时返回 None）。"""
    client = await get_redis()
    if client is None:
        return None
    pubsub = client.pubsub()
    await pubsub.subscribe(channel)
    return pubsub


async def redis_incr(key: str, ttl: int | None = None) -> int:
    """原子自增（限流计数）。"""
    client = await get_redis()
    if client is not None:
        val = await client.incr(key)
        if ttl:
            await client.expire(key, ttl)
        return int(val)
    # 内存兜底：简单计数
    _memory_fallback[key] = _memory_fallback.get(key, 0) + 1
    return _memory_fallback[key]

"""Redis 连接池与客户端管理。

Redis 同时承担：热点缓存、限流计数、JWT 黑名单、WS 广播 Pub/Sub、Celery broker。
未连接时提供安全降级（内存兜底），保证无 Redis 也能本地开发/测试。

内存兜底的**语义必须与 Redis 对齐**，否则会出现只在"无 Redis 环境"触发的怪 bug：
- ``redis_set`` / ``redis_incr`` 携带的 TTL 在内存里同样生效（早期版本曾忽略 TTL，
  导致验证码与限流计数永不过期 —— 无 Redis 的开发环境下，同一邮箱一生只能发 1 次验证码）；
- ``redis_incr`` 的 TTL 只在首次自增（count == 1）时设置（固定窗口），
  与 Redis 侧的 Lua 脚本行为一致。
"""

from __future__ import annotations

from time import monotonic

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger("core.redis")

_redis_pool: aioredis.Redis | None = None
# 无 Redis 时的内存兜底（key → 值）。既有测试会直接窥探/清理这里的明文值，
# 因此过期时间单独放在 _memory_expiry，不改变本字典的结构。
_memory_fallback: dict = {}
# 内存兜底的过期时间表（key → monotonic 时间戳，秒）
_memory_expiry: dict = {}
# 连接失败后的静默期（秒）：期间直接走内存兜底，不再反复付出连接超时。
# 否则 Redis 掉线时，单个请求内的多次 Redis 调用会串行各付一次 0.5s 连接超时。
_REDIS_RETRY_COOLDOWN = 5.0
_redis_retry_after: float = 0.0

# 原子「自增 + 首次设置过期」。不能用「INCR 后无条件 EXPIRE」：被限流拒绝的
# 请求也会把 TTL 续满，固定窗口退化成滑动窗口 —— 用户只要重试间隔小于窗口，
# "每分钟 1 次"就永远等不到重置。count == 1 时才 EXPIRE，窗口到期自然归零。
_INCR_EXPIRE_LUA = """
local v = redis.call('INCR', KEYS[1])
if v == 1 and ARGV[1] ~= '' then
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1]))
end
return v
"""


def _mem_expired(key: str) -> bool:
    """内存兜底键是否已过期；过期则顺手清除并返回 True。"""
    exp = _memory_expiry.get(key)
    if exp is None or exp > monotonic():
        return False
    _memory_fallback.pop(key, None)
    _memory_expiry.pop(key, None)
    return True


async def get_redis() -> aioredis.Redis | None:
    """返回全局 Redis 客户端（懒连接）；不可用时返回 None。

    连接失败进入静默期（``_REDIS_RETRY_COOLDOWN`` 秒），期间调用方直接拿到
    None 走内存兜底，避免每个请求都重复付出连接超时；静默期过后自动重试。
    """
    global _redis_pool, _redis_retry_after
    if _redis_pool is not None:
        return _redis_pool
    if monotonic() < _redis_retry_after:
        return None
    pool: aioredis.Redis | None = None
    try:
        pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=0.5,
        )
        await pool.ping()
        _redis_pool = pool
        _redis_retry_after = 0.0
        _logger.info("redis_connected", url=settings.redis_url)
        return _redis_pool
    except Exception as exc:
        # 失败的半成品连接池要显式关闭，否则底层 socket 泄漏
        if pool is not None:
            try:
                aclose = getattr(pool, "aclose", None)
                if aclose is not None:
                    await aclose()
                else:  # pragma: no cover - redis<5 兼容分支
                    await pool.close()
            except Exception:
                pass
        _redis_retry_after = monotonic() + _REDIS_RETRY_COOLDOWN
        _logger.warning("redis_unavailable_fallback_memory", error=str(exc))
        return None


async def close_redis() -> None:
    """关闭全局 Redis 客户端并释放连接池与内存兜底（应用关闭期调用）。

    幂等：重复调用安全。先摘掉全局句柄再关闭，避免关闭期间新请求复用到
    正在关闭的连接。优先使用 redis-py 5.x 的 ``aclose()``，旧版本回退 ``close()``。
    """
    global _redis_pool, _redis_retry_after
    client, _redis_pool = _redis_pool, None
    _redis_retry_after = 0.0
    _memory_fallback.clear()
    _memory_expiry.clear()
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
        if ttl:
            _memory_expiry[key] = monotonic() + ttl
        else:
            _memory_expiry.pop(key, None)


async def redis_get(key: str) -> str | None:
    """读取键值。"""
    client = await get_redis()
    if client is not None:
        return await client.get(key)
    if key not in _memory_fallback or _mem_expired(key):
        return None
    return _memory_fallback[key]


async def redis_delete(key: str) -> None:
    """删除键。"""
    client = await get_redis()
    if client is not None:
        await client.delete(key)
    else:
        _memory_fallback.pop(key, None)
        _memory_expiry.pop(key, None)


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
    """原子自增（限流计数）。

    ``ttl`` 只在**首次**自增（count == 1）时生效（固定窗口语义）：
    窗口期内被拒绝的请求不会续期，窗口到期计数自然归零。

    Redis 侧用 Lua 保证「INCR + 首次 EXPIRE」原子执行，避免两步之间
    进程崩溃留下一个永不过期的计数键。
    """
    client = await get_redis()
    if client is not None:
        val = await client.eval(_INCR_EXPIRE_LUA, 1, key, str(ttl or ""))
        return int(val)
    # 内存兜底：与 Redis 侧语义对齐（首次自增时落过期时间）
    if _mem_expired(key):
        val = 1
    else:
        val = int(_memory_fallback.get(key, 0)) + 1
    _memory_fallback[key] = val
    if val == 1 and ttl:
        _memory_expiry[key] = monotonic() + ttl
    return val

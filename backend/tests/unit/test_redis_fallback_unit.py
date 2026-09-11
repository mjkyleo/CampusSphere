"""Redis 内存兜底的 TTL 与固定窗口语义回归测试。

背景：内存兜底曾完全忽略 TTL —— 无 Redis 的开发环境下，验证码存储与
限流计数永不过期，表现为"同一邮箱一生只能成功发 1 次验证码，之后永远
提示发送过于频繁"。本文件锁死修复后的语义：

* ``redis_set`` / ``redis_get`` 的 TTL 在内存兜底里同样生效；
* ``redis_incr`` 的 TTL 只在首次自增（count == 1）时设置（固定窗口），
  被拒绝的请求不会把窗口续满。
"""

from __future__ import annotations

import pytest

import app.core.redis as redis_module
from app.core.redis import redis_get, redis_incr, redis_set


async def test_set_with_ttl_expires_in_memory() -> None:
    """带 TTL 写入的键过期后读不到 —— 验证码不能永不过期。"""
    await redis_set("vcode:register:a@x.edu.cn", "123456", ttl=300)
    assert await redis_get("vcode:register:a@x.edu.cn") == "123456"

    # 快进：把过期时间拨到过去
    key_exp = redis_module._memory_expiry["vcode:register:a@x.edu.cn"]
    redis_module._memory_expiry["vcode:register:a@x.edu.cn"] = key_exp - 301

    assert await redis_get("vcode:register:a@x.edu.cn") is None
    # 过期键应被顺手清除，不留僵尸数据
    assert "vcode:register:a@x.edu.cn" not in redis_module._memory_fallback


async def test_set_without_ttl_never_expires() -> None:
    """不带 TTL 的键（如缓存版本号）不进过期表，永不过期。"""
    await redis_set("cache:version:item", "3")
    assert "cache:version:item" not in redis_module._memory_expiry
    assert await redis_get("cache:version:item") == "3"


async def test_incr_window_resets_after_ttl() -> None:
    """限流计数在窗口到期后必须归零（曾因忽略 TTL 被永久锁死）。"""
    key = "vcode:limit:register:a@x.edu.cn"
    assert await redis_incr(key, ttl=60) == 1
    assert await redis_incr(key, ttl=60) == 2

    # 快进 61 秒：窗口到期，下一次自增应重新从 1 开始
    exp = redis_module._memory_expiry[key]
    redis_module._memory_expiry[key] = exp - 61

    assert await redis_incr(key, ttl=60) == 1


async def test_incr_rejected_attempt_does_not_extend_window() -> None:
    """被拒绝的请求不得续满 TTL：否则"每分钟 1 次"会退化成永远发不出去。"""
    key = "vcode:limit:login:13800000000"
    first_exp = None
    for expected in (1, 2, 3):
        assert await redis_incr(key, ttl=60) == expected
        if first_exp is None:
            first_exp = redis_module._memory_expiry[key]
        # 后续自增（包括超出限流被拒的自增）不得刷新过期时间
        assert redis_module._memory_expiry[key] == first_exp


async def test_incr_without_ttl_keeps_counting_forever() -> None:
    """不带 TTL 的自增（如缓存版本号）保持原语义：累加且不过期。"""
    assert await redis_incr("cache:version:item") == 1
    assert await redis_incr("cache:version:item") == 2
    assert "cache:version:item" not in redis_module._memory_expiry

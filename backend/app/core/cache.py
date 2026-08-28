"""热点数据缓存工具：基于 Redis，无 Redis 时自动降级为内存字典。

设计目标（对应审计 P1-9b「热点列表 Redis 缓存」）：
- **防穿透**：对查询结果为空/None 的情况，写入一个带短 TTL 的占位哨兵（NULL_SENTINEL），
  避免对「不存在的 key」反复穿透到数据库。
- **防雪崩**：写入 TTL 叠加随机抖动（jitter），避免大量缓存 key 在同一时刻集中过期，
  造成请求洪峰打满 DB/Redis。
- **失效策略**：采用「命名空间版本号」整体失效，而非枚举/SCAN 具体 key。
  写操作调用 ``invalidate_namespace`` 让版本号 +1，所有旧 key 立即失效（旧版本号拼出的 key 不再命中）。
  该方案对「内存降级」实现同样友好（避免 SCAN 在普通 dict 上不可用的问题）。

缓存键命名规范：
    campus:cache:<namespace>:v<version>:<sha256_of_params>
例如：
    campus:cache:items:v3:a1b2c3d4e5f6...
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Any, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import redis_get, redis_incr, redis_set

_logger = get_logger("core.cache")

_PREFIX = "campus:cache:"
_VERSION_PREFIX = f"{_PREFIX}ver:"
# 空结果占位哨兵：命中它返回短 TTL 的「空」，而非回源
NULL_SENTINEL = "__null__"


def _kwargs_hash(**kwargs: Any) -> str:
    """把查询参数稳定地哈希为 16 位十六进制串，作为缓存键的一部分。"""
    payload = json.dumps(kwargs, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _with_jitter(base: int, jitter: int) -> int:
    """在基础 TTL 上叠加 [0, jitter] 的随机抖动，规避缓存同时过期。"""
    if jitter <= 0:
        return base
    return base + random.randint(0, jitter)


async def _namespace_version(namespace: str) -> int:
    """读取命名空间当前版本号（只读，不递增）。"""
    raw = await redis_get(f"{_VERSION_PREFIX}{namespace}")
    if raw is None:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def make_list_key(namespace: str, version: int, **kwargs: Any) -> str:
    """根据命名空间 + 版本号 + 查询参数生成稳定的缓存键。"""
    return f"{_PREFIX}{namespace}:v{version}:{_kwargs_hash(**kwargs)}"


async def cache_get_json(namespace: str, **kwargs: Any) -> Optional[Any]:
    """读取缓存。

    - 未命中返回 ``None``。
    - 命中空哨兵返回 ``NULL_SENTINEL``（调用方据此直接返回空结果，无需回源）。
    - 命中正常数据返回反序列化后的 Python 对象。
    """
    if not settings.cache_enabled:
        return None
    version = await _namespace_version(namespace)
    key = make_list_key(namespace, version, **kwargs)
    raw = await redis_get(key)
    if raw is None:
        return None
    if raw == NULL_SENTINEL:
        return NULL_SENTINEL
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        # 数据损坏：视为未命中，回源重建
        return None


async def cache_set_json(
    namespace: str,
    value: Any,
    *,
    ttl: int | None = None,
    jitter: int = 15,
    null_ttl: int = 10,
    **kwargs: Any,
) -> None:
    """写入缓存。

    - ``value`` 为 ``None``/空时写入空哨兵（短 TTL，防穿透）。
    - 否则序列化后写入，TTL = (传入 ttl 或 settings.cache_ttl_seconds) + 随机抖动（防雪崩）。
    """
    if not settings.cache_enabled:
        return
    if ttl is None:
        ttl = settings.cache_ttl_seconds
    version = await _namespace_version(namespace)
    key = make_list_key(namespace, version, **kwargs)
    if value is None:
        await redis_set(key, NULL_SENTINEL, ttl=null_ttl)
        return
    try:
        data = json.dumps(value, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        _logger.warning("cache_serialize_failed", namespace=namespace)
        return
    await redis_set(key, data, ttl=_with_jitter(ttl, jitter))


async def invalidate_namespace(namespace: str) -> None:
    """写操作后整体失效某命名空间（版本号 +1）。

    所有旧版本号拼出的 key 立即失效；新请求以新版本号重新回源并写缓存。
    """
    if not settings.cache_enabled:
        return
    await redis_incr(f"{_VERSION_PREFIX}{namespace}")

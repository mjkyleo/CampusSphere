"""单元测试层公共夹具。

单元测试的定义：**不碰数据库、不发网络请求、不读真实外部服务**。
因此本层只提供一件事——保证"内存级外部依赖"在用例之间被清空。

注意：``app.core.redis`` 的内存兜底是模块级字典（值 + 独立的过期时间表），
滑块令牌 / 验证码 / JWT 黑名单都会落在里面。若不清理，用例之间会互相
看到对方的令牌，导致"防重放"类断言随机失败。根 ``conftest.py`` 已经
禁用了真实 Redis 连接，这里只需清空这两个字典即可。
"""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items):
    """自动为本目录下所有用例打 ``unit`` 标记（按目录分层）。"""
    for item in items:
        item.add_marker(pytest.mark.unit)


@pytest.fixture(autouse=True)
def clean_memory_redis():
    """每个用例前后清空 Redis 内存兜底（值 + 过期时间表），保证用例间零残留。"""
    import app.core.redis as redis_module

    redis_module._memory_fallback.clear()
    redis_module._memory_expiry.clear()
    yield
    redis_module._memory_fallback.clear()
    redis_module._memory_expiry.clear()

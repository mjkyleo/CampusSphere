"""关闭期资源释放专项测试。

关注点：应用停止时是否真的把「申请到的资源」还回去。
这类问题在本地开发中不易察觉（进程一退，操作系统会自动回收句柄），
但会在以下场景被放大：

* 开发 / 测试环境反复重启同一进程（uvicorn --reload、pytest 多轮 lifespan）
* 生产滚动更新时旧连接未及时归还，逐步耗尽数据库连接上限
* 单测套件内多次启停导致句柄堆积、用例间相互污染

验证维度
--------
完整性  DB 引擎 / Redis 客户端 / WS 监听任务三类资源全部归零
顺序    后台任务 → 外部连接 → 数据库连接池
容错    任一环节抛错不得阻断后续释放（避免「半释放」）
幂等    未启动或重复关闭的场景下调用安全
兼容    Redis 客户端缺少 aclose() 时回退 close()
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from helpers import run_lifespan


# ---------------------------------------------------------------------------
# 释放完整性
# ---------------------------------------------------------------------------
def test_all_resources_released_after_shutdown(lifecycle_env):
    """一次完整启停后，三类资源句柄都应归零。"""
    import app.core.redis as redis_module
    import app.modules.message.ws as ws_module

    fake_client = AsyncMock()
    redis_module._redis_pool = fake_client
    try:
        with TestClient(lifecycle_env.app) as client:
            assert client.get("/health").status_code == 200, "关闭前服务应可用"
    finally:
        redis_module._redis_pool = None

    assert ws_module.manager._listener_task is None, "WS 监听任务句柄应释放"
    assert redis_module._redis_pool is None, "Redis 客户端句柄应释放"
    assert lifecycle_env.dispose_spy.calls == 1, "数据库连接池应释放一次"


# ---------------------------------------------------------------------------
# 释放顺序
# ---------------------------------------------------------------------------
def test_release_order_is_task_then_redis_then_db(lifecycle_env, monkeypatch):
    """先停后台任务，再关外部连接，最后释放连接池。

    顺序颠倒会导致：任务在连接已关闭后仍尝试收发，抛出噪声异常；
    或连接池先释放而事务尚未提交完成。
    """
    import app.modules.message.ws as ws_module

    order: list[str] = []

    async def _fake_stop_listener():
        order.append("ws")

    async def _fake_close_redis():
        order.append("redis")

    monkeypatch.setattr(ws_module.manager, "stop_listener", _fake_stop_listener)
    monkeypatch.setattr("app.main.close_redis", _fake_close_redis)

    original_dispose = lifecycle_env.dispose_spy.dispose

    async def _spy_dispose(*args, **kwargs):
        order.append("db")
        return await original_dispose(*args, **kwargs)

    monkeypatch.setattr(lifecycle_env.dispose_spy, "dispose", _spy_dispose)

    run_lifespan(lifecycle_env.app)

    assert order == ["ws", "redis", "db"], (
        f"释放顺序应为 后台任务 → 外部连接 → 连接池，实际为 {order}"
    )


# ---------------------------------------------------------------------------
# 容错：任一环节失败不得阻断后续释放
# ---------------------------------------------------------------------------
def test_redis_close_failure_does_not_block_db_release(lifecycle_env, monkeypatch):
    """Redis 关闭抛错时，数据库连接池仍必须被释放。"""
    async def _raise():
        raise RuntimeError("redis close boom")

    monkeypatch.setattr("app.main.close_redis", _raise)

    run_lifespan(lifecycle_env.app)

    assert lifecycle_env.dispose_spy.calls == 1, (
        "Redis 关闭失败不应阻断数据库连接池释放"
    )


def test_ws_stop_failure_does_not_block_redis_and_db_release(lifecycle_env, monkeypatch):
    """WS 监听停止抛错时，Redis 与数据库仍必须被释放。"""
    import app.core.redis as redis_module
    import app.modules.message.ws as ws_module

    async def _raise():
        raise RuntimeError("ws stop boom")

    monkeypatch.setattr(ws_module.manager, "stop_listener", _raise)

    fake_client = AsyncMock()
    redis_module._redis_pool = fake_client
    try:
        run_lifespan(lifecycle_env.app)
    finally:
        redis_module._redis_pool = None

    fake_client.aclose.assert_awaited_once()
    assert lifecycle_env.dispose_spy.calls == 1, "WS 停止失败不应阻断后续释放"


def test_legacy_redis_client_failure_does_not_raise(lifecycle_env):
    """Redis 客户端本身的 close 抛错时，不得向上传播为启动/关闭异常。"""
    import app.core.redis as redis_module

    fake_client = AsyncMock()
    fake_client.aclose.side_effect = RuntimeError("socket already closed")
    redis_module._redis_pool = fake_client
    try:
        run_lifespan(lifecycle_env.app)
    finally:
        redis_module._redis_pool = None

    assert lifecycle_env.dispose_spy.calls == 1, "客户端关闭异常不应中断关闭流程"


# ---------------------------------------------------------------------------
# 幂等与兼容
# ---------------------------------------------------------------------------
def test_close_redis_clears_memory_fallback():
    """close_redis 清空内存兜底字典，避免降级数据跨重启残留。"""
    import app.core.redis as redis_module

    async def _run():
        redis_module._memory_fallback["rate_limit:1.2.3.4"] = 7
        await redis_module.close_redis()
        assert redis_module._memory_fallback == {}, "关闭应清空内存兜底"
        # 幂等：重复调用安全
        await redis_module.close_redis()

    asyncio.run(_run())


def test_close_redis_is_idempotent_without_client():
    """从未建立连接时重复关闭不应抛异常。"""
    import app.core.redis as redis_module

    async def _run():
        redis_module._redis_pool = None
        await redis_module.close_redis()
        await redis_module.close_redis()
        assert redis_module._redis_pool is None

    asyncio.run(_run())


def test_stop_listener_is_idempotent_when_never_started():
    """从未启动监听时重复停止不应抛异常。"""
    import app.modules.message.ws as ws_module

    async def _run():
        ws_module.manager._listener_task = None
        await ws_module.manager.stop_listener()
        await ws_module.manager.stop_listener()
        assert ws_module.manager._listener_task is None

    asyncio.run(_run())


def test_close_redis_falls_back_to_close_when_aclose_missing():
    """旧版 redis-py 客户端没有 aclose() 时，应回退调用 close()。"""
    import app.core.redis as redis_module

    class _LegacyClient:
        """模拟 redis-py < 5 的客户端：只有 close()。"""

        def __init__(self) -> None:
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    async def _run():
        client = _LegacyClient()
        redis_module._redis_pool = client
        await redis_module.close_redis()
        assert client.closed, "缺少 aclose() 时应回退到 close()"
        assert redis_module._redis_pool is None

    asyncio.run(_run())

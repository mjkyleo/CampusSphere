"""应用生命周期测试：启动正确性、关闭资源释放与边界场景。

背景
----
既有 ``conftest.client`` fixture 刻意绕过 lifespan（注释：避免创建 dev.db、
启动后台监听），因此「启动」与「关闭」两条路径长期没有测试覆盖，
shutdown 里漏掉的资源释放也无法被发现。

本模块基于 ``conftest.lifecycle_env``（把全局 engine / SessionLocal 重定向到
临时 SQLite 库）安全地驱动完整 lifespan，验证启停行为与资源释放。

覆盖范围
--------
正常流程
  * 启动后健康检查可达，且真实连到隔离库；根路径受网关保护需鉴权
  * 启动完成管理员引导（seed），重复启动不重复创建（幂等）
  * 关闭后 DB 引擎、Redis 客户端、WS 监听任务均被释放

边界场景
  * 严格模式下的弱网关密钥 / 弱引导密码 → 拒绝启动（SystemExit）
  * Redis 不可用 → 启动不失败（内存降级）
  * 启动中途异常 → 仍执行释放，不留残骸
  * 连续多次启停 → 服务状态保持一致（稳定性）
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.modules.admin.models import AdminUser
from helpers import auth_header, register_login, run_lifespan

# 满足严格校验用的强密钥（≥16 位且非占位值），避免误触发其他的校验分支
_STRONG_GATEWAY_KEY = "test-gateway-key-0123456789"


# ---------------------------------------------------------------------------
# 正常流程
# ---------------------------------------------------------------------------
def test_startup_serves_health_and_enforces_gateway(lifecycle_env):
    """启动后健康检查可达（连的是隔离库）；根路径受网关保护需鉴权。"""
    with TestClient(lifecycle_env.app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        body = health.json()
        assert body["status"] == "ok"
        assert body["database"] == "up"

        # 根路径不在网关白名单内，未携带令牌应被拦截（验证中间件已生效）
        assert client.get("/").status_code == 401


def test_root_returns_service_info_with_token(lifecycle_env):
    """携带有效令牌访问根路径应返回服务元信息。"""
    with TestClient(lifecycle_env.app) as client:
        user = register_login(client, "lifecycle_root")
        resp = client.get("/", headers=auth_header(user["access_token"]))
        assert resp.status_code == 200
        assert resp.json()["service"], "根路径应返回服务名"


def test_startup_seeds_admin_idempotently(lifecycle_env):
    """重复启动只创建一个引导管理员（seed 幂等）。"""
    async def _count_admins() -> int:
        async with lifecycle_env.factory() as session:
            rows = await session.scalars(select(AdminUser))
            return len(rows.all())

    run_lifespan(lifecycle_env.app)
    first = asyncio.run(_count_admins())

    run_lifespan(lifecycle_env.app)
    second = asyncio.run(_count_admins())

    assert first == 1, "首次启动应创建 1 个引导管理员"
    assert second == 1, "重复启动不应重复创建管理员"


def test_shutdown_disposes_db_engine(lifecycle_env):
    """关闭期必须释放数据库连接池，且不残留借出的连接。"""
    run_lifespan(lifecycle_env.app)

    assert lifecycle_env.dispose_spy.calls == 1, (
        "关闭期应恰好调用一次 engine.dispose() 释放连接池"
    )

    # SQLite 使用 NullPool（不池化，无 checkedout 计数）；只有支持计数的池
    # （如生产 PostgreSQL 的 QueuePool）才校验无借出连接，为将来留出回归保护。
    pool = lifecycle_env.engine.sync_engine.pool
    checker = getattr(pool, "checkedout", None)
    if checker is not None:
        assert checker() == 0, "关闭后不应仍有借出未归还的连接"


def test_shutdown_closes_redis_client(lifecycle_env):
    """关闭期必须关闭 Redis 客户端并清空全局句柄。"""
    import app.core.redis as redis_module

    fake_client = AsyncMock()
    redis_module._redis_pool = fake_client
    try:
        run_lifespan(lifecycle_env.app)
    finally:
        redis_module._redis_pool = None

    fake_client.aclose.assert_awaited_once()
    assert redis_module._redis_pool is None, "关闭后全局 Redis 句柄应被清空"


def test_shutdown_stops_ws_listener(lifecycle_env, monkeypatch):
    """关闭期必须取消 WS 广播监听任务（即使任务正在运行）。"""
    import app.modules.message.ws as ws_module

    async def _long_listen():
        await asyncio.sleep(3600)

    monkeypatch.setattr(ws_module.manager, "_redis_listen", _long_listen)
    captured: dict = {}

    async def _drive():
        async with lifecycle_env.app.router.lifespan_context(lifecycle_env.app):
            task = ws_module.manager._listener_task
            captured["task"] = task
            assert task is not None, "启动期应创建监听任务"
            assert not task.done(), "监听任务在启动后应处于运行中"
        captured["after"] = ws_module.manager._listener_task

    asyncio.run(_drive())

    assert captured["task"].cancelled() or captured["task"].done(), (
        "关闭应取消正在运行的监听任务"
    )
    assert captured["after"] is None, "关闭后监听任务句柄应被清空，便于再次启动"


def test_shutdown_is_idempotent(lifecycle_env):
    """重复关闭不应抛异常（stop_listener / close_redis 均幂等）。"""
    import app.modules.message.ws as ws_module

    run_lifespan(lifecycle_env.app)
    run_lifespan(lifecycle_env.app)

    assert ws_module.manager._listener_task is None


# ---------------------------------------------------------------------------
# 边界场景
# ---------------------------------------------------------------------------
def test_weak_gateway_key_refuses_startup(lifecycle_env, monkeypatch):
    """生产严格模式下网关密钥过短 → 拒绝启动。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "admin_gateway_enforce", True)
    monkeypatch.setattr(settings, "admin_gateway_key", "too-short")

    with pytest.raises(SystemExit):
        run_lifespan(lifecycle_env.app)


def test_weak_bootstrap_password_refuses_startup(lifecycle_env, monkeypatch):
    """生产严格模式下引导密码过短 → 拒绝启动。"""
    from app.core.config import settings

    monkeypatch.setattr(settings, "debug", False)
    monkeypatch.setattr(settings, "admin_gateway_enforce", True)
    monkeypatch.setattr(settings, "admin_gateway_key", _STRONG_GATEWAY_KEY)
    monkeypatch.setattr(settings, "admin_bootstrap_enabled", True)
    monkeypatch.setattr(settings, "admin_bootstrap_password", "short")

    with pytest.raises(SystemExit):
        run_lifespan(lifecycle_env.app)


def test_startup_failure_still_releases_resources(lifecycle_env, monkeypatch):
    """启动中途失败也必须走释放逻辑，避免「半启动」残留连接。"""
    import app.main as main_module

    async def _boom(_base):  # 下划线参数：匹配 init_models 签名但无需使用
        raise RuntimeError("init_models failed")

    monkeypatch.setattr(main_module, "init_models", _boom)

    with pytest.raises(RuntimeError, match="init_models failed"):
        run_lifespan(lifecycle_env.app)

    assert lifecycle_env.dispose_spy.calls == 1, "启动中途失败也必须释放数据库连接池"


def test_redis_unavailable_does_not_block_startup(lifecycle_env):
    """Redis 不可用时启动不失败（内存降级），且不留客户端句柄。"""
    import app.core.redis as redis_module

    # conftest 已禁用真实 Redis 连接（from_url 直接抛错），此处验证降级路径
    with TestClient(lifecycle_env.app) as client:
        assert client.get("/health").status_code == 200

    assert redis_module._redis_pool is None, "无 Redis 时不应持有客户端句柄"


def test_repeated_start_stop_is_stable(lifecycle_env):
    """连续多次启停后，服务仍能提供正常响应（无状态污染）。"""
    for _ in range(3):
        with TestClient(lifecycle_env.app) as client:
            body = client.get("/health").json()
            assert body["status"] == "ok", "每次重启后健康检查都应通过"

    with TestClient(lifecycle_env.app) as client:
        assert client.get("/health").json()["status"] == "ok"


def test_metrics_endpoint_available_after_startup(lifecycle_env):
    """启动后 Prometheus 指标端点可用（可观测性依赖它做存活判定）。"""
    with TestClient(lifecycle_env.app) as client:
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "campus_http_requests_total" in resp.text

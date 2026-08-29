"""测试辅助函数：注册登录、认证头、协程运行。"""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient


def register_login(
    client: TestClient, username: str, password: str = "secret123", **extra
) -> dict:
    """注册并登录，返回 login 的 data（含 access_token / refresh_token / user_id）。"""
    r = client.post(
        "/api/auth/register",
        json={"username": username, "password": password, **extra},
    )
    assert r.status_code == 200, f"register failed: {r.text}"
    user_id = r.json()["data"]["id"]
    r2 = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r2.status_code == 200, f"login failed: {r2.text}"
    data = r2.json()["data"]
    data["user_id"] = user_id
    return data


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def seed_admin(session_factory):
    """用配置中的引导账号在测试库创建管理员（不启动 lifespan 时手动调用）。"""
    from app.modules.admin.service import ensure_seed

    async def _seed():
        async with session_factory() as s:
            await ensure_seed(s)

    run_async(_seed())


def admin_login(client: TestClient) -> dict:
    """以配置引导账号登录管理后台，返回 Bearer 头字典。"""
    from app.core.config import settings

    r = client.post(
        "/api/admin/login",
        json={
            "username": settings.admin_bootstrap_username,
            "password": settings.admin_bootstrap_password or "admin123",
        },
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


def run_async(coro):
    """在同步测试中运行一个协程（用于直接调用 service 层）。"""
    return asyncio.run(coro)


def run_lifespan(app) -> None:
    """同步驱动一次完整的「启动 → 关闭」（ASGI lifespan）。

    用于生命周期 / 资源释放测试：相比 ``TestClient`` 上下文管理器，
    它不启动传输层，便于在启停前后精确断言资源状态。
    """
    async def _drive():
        async with app.router.lifespan_context(app):
            pass

    asyncio.run(_drive())


class DisposeSpy:
    """包装 AsyncEngine，记录 dispose 调用并代理其余属性。

    SQLAlchemy 2.0 的 ``AsyncEngine.dispose`` 是只读属性，无法直接
    monkeypatch，因此改为替换 lifespan 的引用点（``app.main.engine``）。
    """

    def __init__(self, real_engine) -> None:
        self._real = real_engine
        self.calls = 0

    async def dispose(self, *args, **kwargs):
        self.calls += 1
        return await self._real.dispose(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self._real, name)

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


def run_async(coro):
    """在同步测试中运行一个协程（用于直接调用 service 层）。"""
    return asyncio.run(coro)

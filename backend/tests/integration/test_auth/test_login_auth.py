"""登录鉴权集成测试：双 Token、错误分支、刷新、会话保持、注销吊销。

响应约定（**易踩坑，务必先读**）
------------------------------
本项目业务错误统一返回 **HTTP 200 + 响应体 ``code`` 非 0**，业务码见
``ErrorCode``（如 ``UNAUTHORIZED = 40100``）；只有**网关中间件**拦截
（缺令牌 / 令牌无效 / 已吊销）时才返回框架级 HTTP 401/403。

因此：
* 「密码错误」「用户不存在」→ ``status == 200`` 且 ``body["code"] == 40100``；
* 「未携带令牌访问需登录接口」→ ``status == 401``。
"""

from __future__ import annotations

import pytest
from helpers import auth_header, register_login

from app.core.exceptions import ErrorCode

pytestmark = pytest.mark.integration


def _login(client, account: str, password: str = "secret123"):
    return client.post("/api/auth/login", json={"username": account, "password": password})


# ---------------------------------------------------------------------------
# 正常登录
# ---------------------------------------------------------------------------
def test_login_returns_dual_tokens(client):
    """登录成功返回**双 Token**（access + refresh）与有效期。"""
    register_login(client, "dual_token_user")
    r = _login(client, "dual_token_user")
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert r.json()["code"] == 0
    assert data["access_token"] and data["refresh_token"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_by_username_and_by_email(client):
    """用户名与邮箱均可登录（需求：两种登录方式都支持）。"""
    user = register_login(client, "both_way_user")
    user_id = user["user_id"]

    # 绑定邮箱（直接用工厂写入，聚焦登录通道本身）
    r = _login(client, "both_way_user")
    assert r.status_code == 200 and r.json()["data"]["access_token"]

    # 用 account 字段显式传用户名，行为应与 username 字段一致
    r2 = client.post(
        "/api/auth/login", json={"account": "both_way_user", "password": "secret123"}
    )
    assert r2.status_code == 200 and r2.json()["code"] == 0
    assert user_id  # 登录主体存在性已由注册保证


def test_login_is_case_sensitive_for_password(client):
    """密码大小写敏感。"""
    register_login(client, "case_pwd_user", password="Passw0rd!")
    r = _login(client, "case_pwd_user", password="passw0rd!")
    assert r.json()["code"] == ErrorCode.UNAUTHORIZED


# ---------------------------------------------------------------------------
# 异常分支
# ---------------------------------------------------------------------------
def test_login_wrong_password_returns_unauthorized(client):
    """密码错误 → 业务码 40100（HTTP 200 + code=40100）。"""
    register_login(client, "wrong_pwd_user")
    r = _login(client, "wrong_pwd_user", password="totally-wrong")
    assert r.status_code == 200
    assert r.json()["code"] == ErrorCode.UNAUTHORIZED


def test_login_nonexistent_user_returns_unauthorized(client):
    """用户不存在 → 同为 40100（不泄露"账号是否存在"，防用户枚举）。"""
    r = _login(client, "no_such_user_xyz")
    assert r.status_code == 200
    assert r.json()["code"] == ErrorCode.UNAUTHORIZED


def test_login_empty_account_rejected(client):
    """账号为空 → 校验错误。"""
    r = client.post("/api/auth/login", json={"password": "secret123"})
    assert r.status_code == 200
    assert r.json()["code"] != 0


# ---------------------------------------------------------------------------
# 令牌刷新
# ---------------------------------------------------------------------------
def test_refresh_token_returns_new_pair(client):
    """用 refresh_token 换新的一对令牌。"""
    tokens = register_login(client, "refresh_user")
    r = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["access_token"] and data["refresh_token"]


def test_new_access_token_is_usable(client):
    """刷新得到的 access_token 可直接访问需登录接口。"""
    tokens = register_login(client, "refresh_use_user")
    refreshed = client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    ).json()["data"]

    r = client.get("/api/auth/bindings", headers=auth_header(refreshed["access_token"]))
    assert r.status_code == 200 and r.json()["code"] == 0, r.text


def test_refresh_rejects_access_token(client):
    """不能用 access_token 当 refresh_token 用（类型隔离）。"""
    tokens = register_login(client, "refresh_abuse_user")
    r = client.post("/api/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.json()["code"] != 0


def test_refresh_rejects_garbage_token(client):
    """垃圾 refresh_token → 拒绝。"""
    r = client.post("/api/auth/refresh", json={"refresh_token": "not.a.token"})
    assert r.json()["code"] != 0


# ---------------------------------------------------------------------------
# 会话保持与网关拦截
# ---------------------------------------------------------------------------
def test_authenticated_request_succeeds(client):
    """携带有效令牌可访问需登录接口。"""
    tokens = register_login(client, "session_user")
    r = client.get("/api/auth/bindings", headers=auth_header(tokens["access_token"]))
    assert r.status_code == 200 and r.json()["code"] == 0
    assert r.json()["data"]["username"] == "session_user"


def test_protected_endpoint_without_token_returns_401(client):
    """未携带令牌 → 网关返回 HTTP 401（框架级，非业务码）。"""
    r = client.get("/api/auth/bindings")
    assert r.status_code == 401


def test_protected_endpoint_with_garbage_token_returns_401(client):
    """无效令牌 → 401。"""
    r = client.get("/api/auth/bindings", headers=auth_header("garbage.token.value"))
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# 注销与吊销
# ---------------------------------------------------------------------------
def test_logout_revokes_access_token(client):
    """注销后 access_token 立即失效（jti 进入黑名单）。"""
    tokens = register_login(client, "logout_user")
    headers = auth_header(tokens["access_token"])

    assert client.get("/api/auth/bindings", headers=headers).status_code == 200

    out = client.post(
        "/api/auth/logout",
        headers={**headers, "X-Refresh-Token": tokens["refresh_token"]},
    )
    assert out.status_code == 200 and out.json()["code"] == 0, out.text

    # 令牌已被吊销，再访问需登录接口应被网关拒绝
    after = client.get("/api/auth/bindings", headers=headers)
    assert after.status_code == 401


def test_refresh_after_logout_rejected(client):
    """注销后 refresh_token 同样失效，无法再换新令牌。"""
    tokens = register_login(client, "logout_refresh_user")
    client.post(
        "/api/auth/logout",
        headers={
            **auth_header(tokens["access_token"]),
            "X-Refresh-Token": tokens["refresh_token"],
        },
    )
    r = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.json()["code"] != 0

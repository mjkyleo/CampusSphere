"""认证流程测试：注册、登录、刷新、注销（黑名单）、错误凭证拒绝。"""

from __future__ import annotations

from helpers import auth_header, register_login


def test_register_and_login(client):
    data = register_login(client, "authuser1")
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user_id"]


def test_me_with_token(client):
    data = register_login(client, "authuser2")
    r = client.get("/api/users/me", headers=auth_header(data["access_token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["username"] == "authuser2"


def test_login_wrong_password_rejected(client):
    register_login(client, "authuser3")
    r = client.post("/api/auth/login", json={"username": "authuser3", "password": "wrongpass"})
    # 业务错误以 HTTP 200 + 业务码 40100 返回，与框架级 401 区分
    assert r.status_code == 200
    assert r.json()["code"] == 40100


def test_refresh_token(client):
    data = register_login(client, "authuser4")
    r = client.post("/api/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["access_token"]


def test_logout_revokes_token(client):
    data = register_login(client, "authuser5")
    old_access = data["access_token"]
    r = client.post(
        "/api/auth/logout",
        headers={**auth_header(old_access), "X-Refresh-Token": data["refresh_token"]},
    )
    assert r.status_code == 200
    # 旧 access token 应被吊销，访问受保护接口返回 401
    r2 = client.get("/api/users/me", headers=auth_header(old_access))
    assert r2.status_code == 401

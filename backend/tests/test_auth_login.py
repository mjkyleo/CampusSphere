"""登录方式测试：用户名登录 / 邮箱登录 / 注册邮箱规则。

需求要点
--------
* 邮箱注册成功后自动生成用户名，用户可用该用户名登录；
* 用户名与邮箱均可作为账号登录；
* 注册时填写邮箱须遵守后台配置的校园邮箱规则（域名白名单 / 正则）——
  用户名注册不能成为绕过校园邮箱限制的后门。
"""

from __future__ import annotations

from helpers import register_login, run_async

from app.modules.auth.service import send_code


def _code(target: str, purpose: str) -> str:
    # limit_per_minute=0 关闭发送频率限制，允许同目标重复发码
    return run_async(send_code(target, purpose, limit_per_minute=0))


def _login(client, account: str, password: str = "secret123"):
    return client.post("/api/auth/login", json={"account": account, "password": password})


# ---------------------------------------------------------------------------
# 用户名登录
# ---------------------------------------------------------------------------
def test_username_registration_then_username_login(client):
    """用户名注册后，用用户名 + 密码登录。"""
    register_login(client, "login_by_name")
    r = _login(client, "login_by_name")
    assert r.json()["code"] == 0, r.text
    assert r.json()["data"]["access_token"]

    # 兼容旧字段 username（等价于 account）
    legacy = client.post(
        "/api/auth/login", json={"username": "login_by_name", "password": "secret123"}
    )
    assert legacy.json()["code"] == 0, legacy.text


def test_email_registration_then_username_login(client):
    """邮箱注册成功后，自动生成的用户名即可用于登录。"""
    email = "toname@example.edu.cn"
    reg = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "secret123", "code": _code(email, "register")},
    )
    assert reg.json()["code"] == 0, reg.text
    username = reg.json()["data"]["username"]
    assert username, "邮箱注册应自动生成用户名"

    r = _login(client, username)
    assert r.json()["code"] == 0, r.text


# ---------------------------------------------------------------------------
# 邮箱登录
# ---------------------------------------------------------------------------
def test_email_registration_then_email_login(client):
    """邮箱注册成功后，可用邮箱 + 密码登录。"""
    email = "bymail@example.edu.cn"
    reg = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "secret123", "code": _code(email, "register")},
    )
    assert reg.json()["code"] == 0, reg.text

    r = _login(client, email)
    assert r.json()["code"] == 0, r.text


def test_email_login_is_case_insensitive(client):
    """邮箱登录忽略大小写，避免用户因大小写输入失败。"""
    email = "CaseUser@example.edu.cn"
    reg = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "secret123", "code": _code(email, "register")},
    )
    assert reg.json()["code"] == 0, reg.text

    assert _login(client, email.upper()).json()["code"] == 0
    assert _login(client, email.lower()).json()["code"] == 0


# ---------------------------------------------------------------------------
# 注册邮箱规则（用户名注册同样受约束）
# ---------------------------------------------------------------------------
def test_username_registration_rejects_non_campus_email(client):
    """用户名注册携带校外邮箱 → 拒绝，与邮箱注册保持同一套规则。"""
    r = client.post(
        "/api/auth/register",
        json={
            "username": "backdoor01",
            "password": "secret123",
            "email": "someone@gmail.com",
        },
    )
    body = r.json()
    assert body["code"] == 42200
    assert "域名" in body["message"]


def test_username_registration_accepts_campus_email(client):
    """用户名注册携带合规校园邮箱 → 允许，并可用邮箱登录。"""
    r = client.post(
        "/api/auth/register",
        json={
            "username": "campus01",
            "password": "secret123",
            "email": "campus01@example.edu.cn",
        },
    )
    assert r.json()["code"] == 0, r.text

    assert _login(client, "campus01@example.edu.cn").json()["code"] == 0


# ---------------------------------------------------------------------------
# 失败场景
# ---------------------------------------------------------------------------
def test_login_unknown_account_rejected(client):
    r = _login(client, "no_such_user_xyz")
    assert r.json()["code"] == 40100


def test_login_wrong_password_rejected(client):
    register_login(client, "wrongpw_user")
    r = _login(client, "wrongpw_user", password="not-the-password")
    assert r.json()["code"] == 40100


def test_login_empty_account_rejected(client):
    r = client.post("/api/auth/login", json={"account": "", "password": "secret123"})
    assert r.json()["code"] != 0

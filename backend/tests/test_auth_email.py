"""邮箱注册、统一登录与多方式绑定测试。

项目约定：业务错误统一 HTTP 200，业务状态码由响应体 code 承载
（code == 0 表示成功；42200 校验失败 / 40100 未认证 / 40300 禁止 / 40900 冲突）。
"""

from __future__ import annotations

from helpers import auth_header, register_login, run_async

from app.core.config import settings
from app.modules.auth import oauth as oauth_mod
from app.modules.auth.service import send_code


def _code(target: str, purpose: str) -> str:
    # limit_per_minute=0 关闭发送频率限制，允许同目标重复发码
    return run_async(send_code(target, purpose, limit_per_minute=0))


def _email_register(client, email, password="secret123", nickname=None, code=None):
    payload = {"email": email, "password": password}
    if nickname:
        payload["nickname"] = nickname
    if code is not None:
        payload["code"] = code
    return client.post("/api/auth/email-register", json=payload)


def _ok(r):
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] == 0, body
    return body["data"]


def _err(r):
    """返回 (code, message)，断言业务失败。"""
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["code"] != 0, body
    return body["code"], body["message"]


def _seed_admin(session_factory):
    """手动初始化默认管理员（测试环境不启动 lifespan）。"""
    from app.modules.admin.service import ensure_seed

    async def _seed():
        async with session_factory() as s:
            await ensure_seed(s)

    run_async(_seed())


def _admin_login(client):
    r = client.post(
        "/api/admin/login",
        json={
            "username": settings.admin_bootstrap_username,
            "password": settings.admin_bootstrap_password or "admin123",
        },
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


# ---------------------------------------------------------------------------


def test_email_register_success(client):
    email = "alice@whu.edu.cn"
    code = _code(email, "register")
    data = _ok(_email_register(client, email, code=code))
    assert data["email"] == email
    assert data["username"]  # 自动生成自定义账号
    assert data["username"].startswith("alice")


def test_email_register_wrong_code(client):
    email = "bob@whu.edu.cn"
    _code(email, "register")
    code, message = _err(_email_register(client, email, code="000000"))
    assert code == 42200
    assert "验证码" in message


def test_email_register_duplicate(client):
    email = "carol@whu.edu.cn"
    _ok(_email_register(client, email, code=_code(email, "register")))
    code, message = _err(_email_register(client, email, code=_code(email, "register")))
    assert code == 40900
    assert "已注册" in message


def test_email_register_rejects_domain(client):
    """域名白名单之外的邮箱不允许注册。

    注意别用 qq.com/163.com 等公共邮箱当反例——它们已在 school.yaml 白名单内。
    """
    code, message = _err(_email_register(client, "evil@evil.com", code="123456"))
    assert code == 42200
    assert "域名" in message


def test_unified_login_with_email_and_username(client):
    """绑定邮箱后，邮箱 / 自定义账号均可 + 密码登录。"""
    email = "dave@whu.edu.cn"
    _ok(_email_register(client, email, code=_code(email, "register")))
    # 邮箱 + 密码（新字段 account）
    data = _ok(client.post("/api/auth/login", json={"account": email, "password": "secret123"}))
    assert data["access_token"]
    # 旧字段 username 仍可用（传邮箱）
    _ok(client.post("/api/auth/login", json={"username": email, "password": "secret123"}))
    # 错误密码
    code, _ = _err(client.post("/api/auth/login", json={"account": email, "password": "wrong-pass"}))
    assert code == 40100


def test_bind_email_phone_and_unified_login(client):
    """用户可补充绑定邮箱/手机号，绑定后支持手机号 + 密码登录。"""
    user = register_login(client, "binder01")
    headers = auth_header(user["access_token"])

    data = _ok(client.get("/api/auth/bindings", headers=headers))
    assert data["email"] is None
    assert data["phone"] is None

    # 绑定邮箱
    email = "eve@whu.edu.cn"
    _ok(client.post("/api/auth/bind/email", json={"email": email, "code": _code(email, "bind_email")}, headers=headers))
    # 绑定手机号
    phone = "13800000001"
    _ok(client.post("/api/auth/bind/phone", json={"phone": phone, "code": _code(phone, "bind_phone")}, headers=headers))

    data = _ok(client.get("/api/auth/bindings", headers=headers))
    assert data["email"] == email
    assert data["phone"] == phone
    assert data["username"] == "binder01"

    # 手机号 + 密码统一登录
    _ok(client.post("/api/auth/login", json={"account": phone, "password": "secret123"}))


def test_bind_conflict_rejected(client):
    """邮箱/手机号已被其他账户绑定 → 拒绝并明确提示。"""
    user_a = register_login(client, "bindera")
    user_b = register_login(client, "binderb")
    email = "frank@whu.edu.cn"

    # A 先绑定邮箱
    _ok(client.post("/api/auth/bind/email", json={"email": email, "code": _code(email, "bind_email")}, headers=auth_header(user_a["access_token"])))

    # B 绑定同一邮箱 → 冲突拒绝
    code, message = _err(
        client.post("/api/auth/bind/email", json={"email": email, "code": _code(email, "bind_email")}, headers=auth_header(user_b["access_token"]))
    )
    assert code == 40900
    assert "已绑定其他账号" in message

    # 手机号冲突同理
    phone = "13900000001"
    _ok(client.post("/api/auth/bind/phone", json={"phone": phone, "code": _code(phone, "bind_phone")}, headers=auth_header(user_a["access_token"])))
    code, message = _err(
        client.post("/api/auth/bind/phone", json={"phone": phone, "code": _code(phone, "bind_phone")}, headers=auth_header(user_b["access_token"]))
    )
    assert code == 40900
    assert "已绑定其他账号" in message


def test_bind_oauth(monkeypatch, client):
    """已登录用户可绑定微信；openid 已被他人占用 → 拒绝。"""
    async def _fake_exchange_wechat(code: str) -> str:
        return "wx_openid_001"

    monkeypatch.setattr(oauth_mod, "_exchange_wechat_openid", _fake_exchange_wechat)

    user_a = register_login(client, "oaba")
    _ok(client.post("/api/auth/bind/oauth", json={"provider": "wechat", "code": "auth-code-a"}, headers=auth_header(user_a["access_token"])))
    data = _ok(client.get("/api/auth/bindings", headers=auth_header(user_a["access_token"])))
    assert "wechat" in data["oauth"]

    # 用户 B 绑定同一 openid → 冲突
    user_b = register_login(client, "oabb")
    code, message = _err(
        client.post("/api/auth/bind/oauth", json={"provider": "wechat", "code": "auth-code-a"}, headers=auth_header(user_b["access_token"]))
    )
    assert code == 40900
    assert "已绑定其他账号" in message

    # 重复绑定自身 → 明确提示已绑定
    code, _ = _err(
        client.post("/api/auth/bind/oauth", json={"provider": "wechat", "code": "auth-code-a"}, headers=auth_header(user_a["access_token"]))
    )
    assert code == 40900


def test_unbind_email(client):
    user = register_login(client, "unbinder")
    headers = auth_header(user["access_token"])
    email = "grace@whu.edu.cn"
    _ok(client.post("/api/auth/bind/email", json={"email": email, "code": _code(email, "bind_email")}, headers=headers))

    _ok(client.delete("/api/auth/unbind/email", headers=headers))
    data = _ok(client.get("/api/auth/bindings", headers=headers))
    assert data["email"] is None
    # 解绑后该邮箱可被其他账户绑定
    other = register_login(client, "unbinder2")
    _ok(client.post("/api/auth/bind/email", json={"email": email, "code": _code(email, "bind_email")}, headers=auth_header(other["access_token"])))


def test_admin_email_config_overrides_domain(client, session_factory):
    """后台可动态配置邮箱注册域名白名单并实时生效。"""
    _seed_admin(session_factory)
    admin_headers = _admin_login(client)

    # 读取默认配置（来自 school.yaml）
    data = _ok(client.get("/api/admin/auth/email-config", headers=admin_headers))
    assert data["enabled"] is True
    assert "whu.edu.cn" in data["domains"]

    # 更新为新的域名白名单
    _ok(client.put("/api/admin/auth/email-config", json={"enabled": True, "domains": ["school.cn"], "pattern": ""}, headers=admin_headers))

    # 新域名可注册
    email_new = "student@school.cn"
    _ok(_email_register(client, email_new, code=_code(email_new, "register")))
    # 旧域名被移除 → 拒绝
    email_old = "old@whu.edu.cn"
    code, _ = _err(_email_register(client, email_old, code=_code(email_old, "register")))
    assert code == 42200


def test_email_register_disabled_by_admin(client, session_factory):
    """后台关闭邮箱注册后，注册被拒绝。"""
    _seed_admin(session_factory)
    admin_headers = _admin_login(client)
    _ok(client.put("/api/admin/auth/email-config", json={"enabled": False, "domains": [], "pattern": ""}, headers=admin_headers))

    email = "henry@whu.edu.cn"
    code, message = _err(_email_register(client, email, code=_code(email, "register")))
    assert code == 40300
    assert "未开放" in message

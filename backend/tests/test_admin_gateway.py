"""管理后台安全测试：网关隐藏、discover 换令牌、promote 提权、弱配置 fail-fast。

注意：conftest 的 ``_relax_admin_gateway`` 默认把 ``admin_gateway_enforce`` 置为 False，
以便既有管理后台测试无需网关令牌即可通过。本文件中的用例显式开启强制校验，验证真实安全行为。
"""

from __future__ import annotations

import pytest

from app.core.config import settings, validate_admin_security
from app.modules.admin.service import ensure_seed
from helpers import auth_header, register_login, run_async

GATEWAY_KEY = "test-gateway-key-1234567890"
SECRET_KEY = "test-secret-key-for-gateway"
ADMIN_USER = "testadmin"
ADMIN_PASS = "test-admin-pass-123456"


@pytest.fixture
def enforced_gateway():
    """临时开启网关强制校验，并固定网关密钥，测试结束后恢复原值。"""
    old_enforce = settings.admin_gateway_enforce
    old_key = settings.admin_gateway_key
    old_secret = settings.secret_key
    settings.admin_gateway_enforce = True
    settings.admin_gateway_key = GATEWAY_KEY
    settings.secret_key = SECRET_KEY
    yield
    settings.admin_gateway_enforce = old_enforce
    settings.admin_gateway_key = old_key
    settings.secret_key = old_secret


def _gateway_token(client) -> str:
    d = client.post("/api/admin/discover", json={"gateway_key": GATEWAY_KEY})
    assert d.status_code == 200, d.text
    return d.json()["data"]["gateway_token"]


def test_gateway_masks_admin_endpoints(client, enforced_gateway):
    """未携带网关令牌访问 /api/admin/* 一律 404（对外表现为端点不存在）。"""
    # 无任何网关头
    r1 = client.get("/api/admin/users")
    assert r1.status_code == 404, r1.text
    # 错误的网关令牌
    r2 = client.get("/api/admin/users", headers={"X-Admin-Gateway": "wrong-token"})
    assert r2.status_code == 404, r2.text
    # 正确网关令牌但无管理员 Bearer：网关放行，中间件要求鉴权 -> 401（非 404）
    gw = _gateway_token(client)
    r3 = client.get("/api/admin/users", headers={"X-Admin-Gateway": gw})
    assert r3.status_code == 401, r3.text


def test_discover_requires_correct_key(client, enforced_gateway):
    """discover 仅接受正确网关密钥，错误密钥一律 404（不泄露管理端存在）。"""
    ok = client.post("/api/admin/discover", json={"gateway_key": GATEWAY_KEY})
    assert ok.status_code == 200
    assert ok.json()["data"]["gateway_token"]

    bad = client.post("/api/admin/discover", json={"gateway_key": "not-the-key"})
    assert bad.status_code == 404, bad.text


def test_admin_login_requires_gateway(client, session_factory, enforced_gateway):
    """管理员登录也必须携带网关令牌，否则 404。"""
    async def _seed():
        async with session_factory() as db:
            await ensure_seed(db)

    run_async(_seed())

    # 无网关令牌 -> 404
    r = client.post(
        "/api/admin/login",
        json={"username": settings.admin_bootstrap_username, "password": settings.admin_bootstrap_password or "admin123"},
    )
    assert r.status_code == 404, r.text

    # 带正确网关令牌 -> 200
    gw = _gateway_token(client)
    r2 = client.post(
        "/api/admin/login",
        json={"username": settings.admin_bootstrap_username, "password": settings.admin_bootstrap_password or "admin123"},
        headers={"X-Admin-Gateway": gw},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["data"]["access_token"]


def test_promote_user_to_admin(client, session_factory, enforced_gateway):
    """管理员可将普通用户提升为管理员，并可用新账号登录后台。"""
    # 配置并 seed 一个测试管理员
    old_user = settings.admin_bootstrap_username
    old_pass = settings.admin_bootstrap_password
    settings.admin_bootstrap_username = ADMIN_USER
    settings.admin_bootstrap_password = ADMIN_PASS

    async def _seed():
        async with session_factory() as db:
            await ensure_seed(db)

    run_async(_seed())

    gw = _gateway_token(client)
    login = client.post(
        "/api/admin/login",
        json={"username": ADMIN_USER, "password": ADMIN_PASS},
        headers={"X-Admin-Gateway": gw},
    )
    assert login.status_code == 200, login.text
    admin_jwt = login.json()["data"]["access_token"]

    # 创建一个普通用户
    normal = register_login(client, "promoteme1", "secret123")
    user_id = normal["user_id"]

    # 提权
    pr = client.post(
        f"/api/admin/users/{user_id}/promote",
        json={"password": "newadmin-123456"},
        headers={"Authorization": f"Bearer {admin_jwt}", "X-Admin-Gateway": gw},
    )
    assert pr.status_code == 200, pr.text
    assert pr.json()["data"]["is_admin"] is True

    # 新管理员可用新账号登录后台
    gw2 = _gateway_token(client)
    new_login = client.post(
        "/api/admin/login",
        json={"username": "promoteme1", "password": "newadmin-123456"},
        headers={"X-Admin-Gateway": gw2},
    )
    assert new_login.status_code == 200, new_login.text
    new_jwt = new_login.json()["data"]["access_token"]
    me = client.get("/api/admin/me", headers={"Authorization": f"Bearer {new_jwt}", "X-Admin-Gateway": gw2})
    assert me.status_code == 200, me.text

    # 还原配置
    settings.admin_bootstrap_username = old_user
    settings.admin_bootstrap_password = old_pass


def test_weak_config_fail_fast():
    """弱安全配置在生产（非 debug + 强制网关）下应启动期 fail-fast。"""
    old = {
        "debug": settings.debug,
        "enforce": settings.admin_gateway_enforce,
        "key": settings.admin_gateway_key,
        "passwd": settings.admin_bootstrap_password,
        "min": settings.admin_bootstrap_min_length,
    }
    try:
        settings.debug = False
        settings.admin_gateway_enforce = True
        settings.admin_gateway_key = ""  # 缺失/过短
        settings.admin_bootstrap_password = "short"  # 弱密码
        with pytest.raises(SystemExit):
            validate_admin_security()
    finally:
        settings.debug = old["debug"]
        settings.admin_gateway_enforce = old["enforce"]
        settings.admin_gateway_key = old["key"]
        settings.admin_bootstrap_password = old["passwd"]
        settings.admin_bootstrap_min_length = old["min"]


def test_strong_config_passes_validation():
    """强配置（足够长的网关密钥 + bootstrap 密码）应通过校验。"""
    old = {
        "debug": settings.debug,
        "enforce": settings.admin_gateway_enforce,
        "key": settings.admin_gateway_key,
        "passwd": settings.admin_bootstrap_password,
        "min": settings.admin_bootstrap_min_length,
    }
    try:
        settings.debug = False
        settings.admin_gateway_enforce = True
        settings.admin_gateway_key = "a-strong-gateway-key-1234567890"
        settings.admin_bootstrap_password = "a-strong-bootstrap-pass-123"
        settings.admin_bootstrap_min_length = 16
        validate_admin_security()  # 不应抛异常
    finally:
        settings.debug = old["debug"]
        settings.admin_gateway_enforce = old["enforce"]
        settings.admin_gateway_key = old["key"]
        settings.admin_bootstrap_password = old["passwd"]
        settings.admin_bootstrap_min_length = old["min"]

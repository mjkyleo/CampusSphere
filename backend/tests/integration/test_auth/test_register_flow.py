"""邮箱注册全流程集成测试：**滑块 → 验证码 → 注册 → 自动登录**。

这是新用户进入平台的第一步，也是被脚本攻击风险最高的入口
（刷验证码轰炸邮箱、批量注册垃圾账号），因此正常流程与**每一条防御分支**
都必须有回归保护。

测试环境说明
------------
服务端未配置 SMTP 时 ``send-code`` 会在响应里回传 ``debug_code``，
集成测试据此拿到真实验证码完成注册，无需真实邮箱。
"""

from __future__ import annotations

import json
import uuid

import pytest

from app.core.config import settings

pytestmark = pytest.mark.integration

_SLIDER_PREFIX = "captcha:slider:"
_VCODE_PREFIX = "vcode:register:"

# 与 config/school.yaml 的 auth.email_register.domains 保持一致；
# 若调整该文件需同步更新此常量，否则注册用例会被白名单拦截。
DEFAULT_ALLOWED_DOMAIN = "example.edu.cn"


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------
def _uniq_email(domain: str = DEFAULT_ALLOWED_DOMAIN) -> str:
    """生成唯一邮箱，避免跨用例的验证码/唯一索引互相干扰。

    默认域名取 ``config/school.yaml`` 的 ``auth.email_register.domains`` 首项，
    与真实默认配置保持一致——用不存在的域名会被白名单直接拦下。
    """
    return f"stu_{uuid.uuid4().hex[:10]}@{domain}"


def _human_track(target_x: float, points: int = 12) -> list[list[float]]:
    """先快后慢、步进不等的"人类"拖动轨迹。"""
    return [
        [i * 30, round(target_x * (i / (points - 1)) ** 0.75, 2), 40.0]
        for i in range(points)
    ]


def _complete_slider(client) -> str:
    """走完一次滑块验证，返回票据。

    缺口横坐标不下发给前端，测试直接从 Redis 内存兜底里**窥探**服务端状态，
    这样既能构造"命中"输入，又不依赖任何后门接口。
    """
    r = client.get("/api/auth/captcha/slider")
    assert r.status_code == 200, r.text
    data = r.json()["data"]

    import app.core.redis as redis_module

    raw = redis_module._memory_fallback[f"{_SLIDER_PREFIX}{data['token']}"]
    target_x = float(json.loads(raw)["x"])

    r2 = client.post(
        "/api/auth/captcha/verify",
        json={
            "token": data["token"],
            "offset_x": target_x,
            "track": _human_track(target_x),
            "elapsed_ms": 600,
        },
    )
    assert r2.status_code == 200, r2.text
    return r2.json()["data"]["ticket"]


def _send_code(client, email: str, ticket=None, purpose: str = "register") -> str:
    """发送验证码并返回验证码（debug 模式直接回传）。"""
    payload = {"target": email, "purpose": purpose}
    if ticket is not None:
        payload["captcha_ticket"] = ticket
    r = client.post("/api/auth/send-code", json=payload)
    assert r.status_code == 200, r.text
    code = r.json()["data"]["debug_code"]
    assert code, "测试环境未配置 SMTP，debug_code 应当回传验证码"
    return code


@pytest.fixture
def captcha_enabled(monkeypatch):
    """临时开启滑块验证（根 conftest 默认关闭，以免影响既有用例）。"""
    monkeypatch.setattr(settings, "captcha_enabled", True)
    yield


@pytest.fixture
def whitelist_only(monkeypatch):
    """把邮箱规则收敛为"仅 DEFAULT_ALLOWED_DOMAIN"，用于验证域名白名单。

    直接替换 service 层的规则读取函数，避免依赖管理后台接口的 payload 细节，
    从而把测试焦点保持在「白名单校验」本身。
    """
    import app.modules.auth.service as auth_service

    async def _rule(_db):
        return {"enabled": True, "domains": [DEFAULT_ALLOWED_DOMAIN], "pattern": ""}

    monkeypatch.setattr(auth_service, "get_email_register_rule", _rule)


# ---------------------------------------------------------------------------
# 正常流程
# ---------------------------------------------------------------------------
def test_register_full_flow_slider_code_register_autologin(client, captcha_enabled):
    """完整旅程：滑块 → 验证码 → 注册 → 返回双 Token（注册即登录）。"""
    email = _uniq_email()

    ticket = _complete_slider(client)
    code = _send_code(client, email, ticket=ticket)

    r = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "Str0ng!Pass", "nickname": "新生小李", "code": code},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]

    # 注册即登录：直接签发双 Token
    assert data["access_token"] and data["refresh_token"]
    assert data["token_type"] == "bearer"
    # 账号由邮箱前缀自动生成，供后续用户名登录使用
    assert data["username"] == email.split("@")[0]
    assert data["email"] == email


def test_registered_user_can_login_with_generated_username(client, captcha_enabled):
    """注册成功后可用**自动生成的用户名**登录（需求：支持用户名登录）。"""
    email = _uniq_email()
    ticket = _complete_slider(client)
    code = _send_code(client, email, ticket=ticket)

    reg = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "Str0ng!Pass", "code": code},
    )
    assert reg.status_code == 200, reg.text
    username = reg.json()["data"]["username"]

    login = client.post(
        "/api/auth/login", json={"username": username, "password": "Str0ng!Pass"}
    )
    assert login.status_code == 200, login.text
    assert login.json()["data"]["access_token"]


def test_register_is_case_insensitive_for_email(client, captcha_enabled):
    """邮箱大小写不敏感：大写注册后可用小写登录（域名大小写不应产生重复账号）。"""
    email = _uniq_email()
    ticket = _complete_slider(client)
    code = _send_code(client, email, ticket=ticket)

    reg = client.post(
        "/api/auth/email-register",
        json={"email": email.upper(), "password": "Str0ng!Pass", "code": code},
    )
    assert reg.status_code == 200, reg.text
    assert reg.json()["data"]["email"] == email.lower()


# ---------------------------------------------------------------------------
# 异常流程
# ---------------------------------------------------------------------------
def test_send_code_requires_slider_ticket(client, captcha_enabled):
    """开启滑块后，无票据直接请求验证码 → 拒绝（防脚本绕过滑块刷验证码）。"""
    r = client.post(
        "/api/auth/send-code", json={"target": _uniq_email(), "purpose": "register"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] != 0  # 业务错误码非 0
    assert "滑块" in body["message"]


def test_send_code_rejects_replayed_ticket(client, captcha_enabled):
    """票据一次性：同一张票据不能用来发第二封验证码（防重放）。"""
    ticket = _complete_slider(client)
    assert _send_code(client, _uniq_email(), ticket=ticket)

    r = client.post(
        "/api/auth/send-code",
        json={"target": _uniq_email(), "purpose": "register", "captcha_ticket": ticket},
    )
    assert r.json()["code"] != 0


def test_register_rejects_wrong_code(client, captcha_enabled):
    """验证码错误 → 注册失败。"""
    email = _uniq_email()
    ticket = _complete_slider(client)
    _send_code(client, email, ticket=ticket)

    r = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "Str0ng!Pass", "code": "000000"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["code"] != 0 and "验证码" in body["message"]


def test_register_rejects_expired_code(client, captcha_enabled):
    """验证码过期（存储被清除）→ 注册失败，不能凭旧码注册。"""
    email = _uniq_email()
    ticket = _complete_slider(client)
    _send_code(client, email, ticket=ticket)

    # 模拟 TTL 到期：直接抹掉服务端存储的验证码
    import app.core.redis as redis_module

    redis_module._memory_fallback.pop(f"{_VCODE_PREFIX}{email}", None)

    r = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "Str0ng!Pass", "code": "123456"},
    )
    assert r.json()["code"] != 0


def test_register_rejects_duplicate_email(client, captcha_enabled):
    """同一邮箱重复注册 → 冲突，不产生第二个账号。"""
    email = _uniq_email()

    ticket1 = _complete_slider(client)
    code1 = _send_code(client, email, ticket=ticket1)
    first = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "Str0ng!Pass", "code": code1},
    )
    assert first.status_code == 200 and first.json()["code"] == 0, first.text

    # 同一 target 的发送频率限制为 1 次/分钟：清掉计数以模拟"隔了一分钟再获取"，
    # 否则第二次 send-code 会先被限流拦下，测试根本走不到重复校验分支。
    import app.core.redis as redis_module

    redis_module._memory_fallback.pop(f"vcode:limit:register:{email}", None)

    ticket2 = _complete_slider(client)
    code2 = _send_code(client, email, ticket=ticket2)
    second = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "Str0ng!Pass", "code": code2},
    )
    assert second.json()["code"] != 0
    assert "已注册" in second.json()["message"]


def test_register_rejects_non_whitelisted_domain(client, captcha_enabled, whitelist_only):
    """域名不在白名单 → 拒绝（防止用任意邮箱批量注册）。"""
    email = _uniq_email(domain="gmail.com")
    ticket = _complete_slider(client)
    _send_code(client, email, ticket=ticket)

    r = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "Str0ng!Pass", "code": "123456"},
    )
    assert r.json()["code"] != 0
    assert "域名" in r.json()["message"]


def test_register_accepts_whitelisted_domain(client, captcha_enabled, whitelist_only):
    """对照用例：白名单域名放行（确保上一条不是"一律拒绝"的假阳性）。"""
    email = _uniq_email(domain=DEFAULT_ALLOWED_DOMAIN)
    ticket = _complete_slider(client)
    code = _send_code(client, email, ticket=ticket)

    r = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "Str0ng!Pass", "code": code},
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text


def test_register_rejects_weak_password(client, captcha_enabled):
    """密码过短 → 校验层拒绝（schema 约束 min_length=6）。"""
    email = _uniq_email()
    ticket = _complete_slider(client)
    code = _send_code(client, email, ticket=ticket)

    r = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "123", "code": code},
    )
    assert r.status_code == 422  # Pydantic 校验失败

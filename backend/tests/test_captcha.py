"""滑块验证与验证码防滥用测试。

覆盖两条主线：
1. 滑块本身：生成不泄露缺口坐标、校验容差、令牌一次性、拦截脚本特征（匀速轨迹/瞬时完成）
2. 防绕过：send-code 在开启滑块后必须凭票据，且票据不可重放

完整链路（滑块 → 发码 → 邮箱注册 → 用户名/邮箱登录）在末尾串联验证。
"""

from __future__ import annotations

import json

import pytest
from helpers import run_async

from app.core.config import settings
from app.modules.auth.service import send_code


def _target_x(token: str) -> int:
    """读取缺口横坐标。

    仅测试可达：真实环境中该值只存在于 Redis（此处走内存降级）。
    """
    import app.core.redis as redis_module

    raw = redis_module._memory_fallback.get(f"captcha:slider:{token}")
    assert raw, "滑块令牌未落库"
    return int(json.loads(raw)["x"])


def _human_track(points: int = 10) -> list[list[float]]:
    """模拟人类轨迹：非匀速、步进合理、整体向前。"""
    return [[i * 35, i * 9 + (i % 3) * 2] for i in range(points)]


def _robot_track(points: int = 10) -> list[list[float]]:
    """脚本轨迹：完全匀速（每步位移一致）。"""
    return [[i * 30, i * 10] for i in range(points)]


def _pass_slider(client) -> str:
    """完成一次滑块验证，返回票据。"""
    data = client.get("/api/auth/captcha/slider").json()["data"]
    r = client.post(
        "/api/auth/captcha/verify",
        json={
            "token": data["token"],
            "offset_x": _target_x(data["token"]),
            "track": _human_track(),
            "elapsed_ms": 900,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["code"] == 0, r.text
    return r.json()["data"]["ticket"]


@pytest.fixture
def captcha_on(monkeypatch):
    """显式开启滑块验证（conftest 默认为关闭，以免影响既有用例）。"""
    monkeypatch.setattr(settings, "captcha_enabled", True)


# ---------------------------------------------------------------------------
# 滑块生成
# ---------------------------------------------------------------------------
def test_slider_returns_images_without_secret(client):
    """返回两张图 + 尺寸，且绝不泄露缺口横坐标。"""
    r = client.get("/api/auth/captcha/slider")
    assert r.status_code == 200
    data = r.json()["data"]

    assert data["background"].startswith("data:image/png;base64,")
    assert data["slider"].startswith("data:image/png;base64,")
    assert data["width"] == 320
    assert data["height"] == 160
    assert data["slider_size"] == 52
    assert data["expires_in"] > 0
    # 横坐标只在服务端；若下发，攻击者无需拖动即可通过
    assert "x" not in data


def test_slider_position_randomized(client):
    """两次生成的缺口位置不应固定在同一点（否则可被硬编码绕过）。"""
    xs = set()
    for _ in range(6):
        data = client.get("/api/auth/captcha/slider").json()["data"]
        xs.add(_target_x(data["token"]))
    assert len(xs) > 1, "缺口位置应随机"


# ---------------------------------------------------------------------------
# 滑块校验
# ---------------------------------------------------------------------------
def test_slider_verify_success_issues_ticket(client):
    data = client.get("/api/auth/captcha/slider").json()["data"]
    target = _target_x(data["token"])

    r = client.post(
        "/api/auth/captcha/verify",
        json={
            "token": data["token"],
            "offset_x": target + settings.captcha_tolerance_px - 1,  # 容差内
            "track": _human_track(),
            "elapsed_ms": 800,
        },
    )
    body = r.json()
    assert body["code"] == 0, body
    assert body["data"]["ticket"]


def test_slider_token_is_one_time(client):
    """令牌一次性：防止反复试探坐标。"""
    data = client.get("/api/auth/captcha/slider").json()["data"]
    target = _target_x(data["token"])
    payload = {
        "token": data["token"],
        "offset_x": target,
        "track": _human_track(),
        "elapsed_ms": 800,
    }
    assert client.post("/api/auth/captcha/verify", json=payload).json()["code"] == 0

    again = client.post("/api/auth/captcha/verify", json=payload)
    assert again.json()["code"] != 0, "同一令牌不应二次通过"


def test_slider_rejects_wrong_offset(client):
    data = client.get("/api/auth/captcha/slider").json()["data"]
    target = _target_x(data["token"])

    r = client.post(
        "/api/auth/captcha/verify",
        json={
            "token": data["token"],
            "offset_x": target + settings.captcha_tolerance_px + 20,
            "track": _human_track(),
            "elapsed_ms": 800,
        },
    )
    assert r.json()["code"] != 0


def test_slider_rejects_robot_track(client):
    """匀速轨迹（脚本特征）应被拒绝，即使坐标正确。"""
    data = client.get("/api/auth/captcha/slider").json()["data"]
    r = client.post(
        "/api/auth/captcha/verify",
        json={
            "token": data["token"],
            "offset_x": _target_x(data["token"]),
            "track": _robot_track(),
            "elapsed_ms": 800,
        },
    )
    assert r.json()["code"] != 0


def test_slider_rejects_instant_drag(client):
    """耗时过短（脚本瞬时提交）应被拒绝。"""
    data = client.get("/api/auth/captcha/slider").json()["data"]
    r = client.post(
        "/api/auth/captcha/verify",
        json={
            "token": data["token"],
            "offset_x": _target_x(data["token"]),
            "track": _human_track(),
            "elapsed_ms": 5,
        },
    )
    assert r.json()["code"] != 0


def test_slider_rejects_unknown_token(client):
    r = client.post(
        "/api/auth/captcha/verify",
        json={
            "token": "nonexistent-token",
            "offset_x": 10,
            "track": _human_track(),
            "elapsed_ms": 800,
        },
    )
    assert r.json()["code"] != 0


# ---------------------------------------------------------------------------
# send-code 防绕过
# ---------------------------------------------------------------------------
def test_send_code_requires_ticket_when_enabled(client, captcha_on):
    """开启滑块后，无票据直接发码应被拒绝。"""
    r = client.post(
        "/api/auth/send-code",
        json={"target": "attacker@whu.edu.cn", "purpose": "register"},
    )
    body = r.json()
    assert body["code"] == 42200
    assert "滑块" in body["message"]


def test_send_code_accepts_valid_ticket(client, captcha_on):
    ticket = _pass_slider(client)
    r = client.post(
        "/api/auth/send-code",
        json={
            "target": "student@whu.edu.cn",
            "purpose": "register",
            "captcha_ticket": ticket,
        },
    )
    assert r.json()["code"] == 0, r.text


def test_ticket_cannot_be_replayed(client, captcha_on):
    """票据一次性：重放应被拒绝，避免一次滑块刷大量验证码。"""
    ticket = _pass_slider(client)
    payload = {
        "target": "replay@whu.edu.cn",
        "purpose": "register",
        "captcha_ticket": ticket,
    }
    assert client.post("/api/auth/send-code", json=payload).json()["code"] == 0

    replay = client.post("/api/auth/send-code", json=payload)
    assert replay.json()["code"] != 0, "票据不应可重放"


def test_send_code_without_ticket_when_disabled(client):
    """关闭滑块（测试/内网环境）时保持原有行为，不需要票据。"""
    assert settings.captcha_enabled is False, "conftest 应默认关闭滑块"
    r = client.post(
        "/api/auth/send-code",
        json={"target": "internal@whu.edu.cn", "purpose": "register"},
    )
    assert r.json()["code"] == 0, r.text


def test_captcha_config_exposes_switch(client):
    data = client.get("/api/auth/captcha/config").json()["data"]
    assert data["enabled"] is False  # conftest 默认关闭


# ---------------------------------------------------------------------------
# 验证码防暴力枚举
# ---------------------------------------------------------------------------
def test_verification_code_locks_after_max_attempts(client):
    """连续错误尝试达到上限后，正确验证码也被作废。"""
    email = "lockme@whu.edu.cn"
    correct = run_async(send_code(email, "register", limit_per_minute=0))

    for _ in range(settings.code_max_attempts):
        r = client.post(
            "/api/auth/email-register",
            json={"email": email, "password": "secret123", "code": "000000"},
        )
        assert r.json()["code"] != 0

    # 达到上限后，即便提交正确验证码也应失败（验证码已被作废）
    r = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "secret123", "code": correct},
    )
    assert r.json()["code"] != 0


def test_new_code_resets_attempt_counter(client):
    """重新获取验证码后，之前的错误尝试不应继续累计。"""
    email = "reset@whu.edu.cn"
    run_async(send_code(email, "register", limit_per_minute=0))
    for _ in range(settings.code_max_attempts):
        client.post(
            "/api/auth/email-register",
            json={"email": email, "password": "secret123", "code": "000000"},
        )

    fresh = run_async(send_code(email, "register", limit_per_minute=0))
    r = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "secret123", "code": fresh},
    )
    assert r.json()["code"] == 0, r.text


# ---------------------------------------------------------------------------
# 完整链路
# ---------------------------------------------------------------------------
def test_full_flow_slider_to_login(client, captcha_on):
    """滑块 → 发码 → 邮箱注册 → 用户名登录 / 邮箱登录 均可。"""
    email = "flowuser@whu.edu.cn"
    ticket = _pass_slider(client)

    sent = client.post(
        "/api/auth/send-code",
        json={"target": email, "purpose": "register", "captcha_ticket": ticket},
    )
    assert sent.json()["code"] == 0, sent.text
    code = sent.json()["data"]["debug_code"]
    assert code, "开启 EXPOSE_VERIFICATION_CODE 时应返回 debug_code 便于联调"

    reg = client.post(
        "/api/auth/email-register",
        json={"email": email, "password": "secret123", "code": code},
    )
    assert reg.json()["code"] == 0, reg.text
    username = reg.json()["data"]["username"]

    # 注册成功后：用户名 + 密码
    by_name = client.post(
        "/api/auth/login", json={"account": username, "password": "secret123"}
    )
    assert by_name.json()["code"] == 0, by_name.text

    # 注册成功后：邮箱 + 密码
    by_mail = client.post(
        "/api/auth/login", json={"account": email, "password": "secret123"}
    )
    assert by_mail.json()["code"] == 0, by_mail.text

    # 错误密码仍被拒绝
    wrong = client.post(
        "/api/auth/login", json={"account": username, "password": "bad-password"}
    )
    assert wrong.json()["code"] == 40100

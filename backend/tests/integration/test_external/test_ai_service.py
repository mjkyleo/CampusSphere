"""AI（Gemini）服务集成测试：**mock 固定文案 + 降级逻辑 + 开关**。

策略：
* 用 ``monkeypatch`` 替换 ``app.modules.ai.service._call_gemini``，
  返回固定文案，验证**请求参数**与**响应透传**；
* 让被 mock 的函数抛 ``BizError``，验证上游故障时的**降级行为**
  （返回业务错误码，**绝不能返回假数据**）；
* 功能开关关闭时返回 40300。

注意 mock 点选在 ``_call_gemini`` 而非 HTTP 层：既避免真实外网调用，
又能覆盖到"配置校验 → prompt 组装 → 结果返回"的完整业务链路。
"""

from __future__ import annotations

import pytest
from helpers import auth_header, register_login

import app.modules.ai.service as ai_service
from app.core.exceptions import BizError, ErrorCode

pytestmark = pytest.mark.integration


@pytest.fixture
def ai_ready(monkeypatch):
    """开启 AI 功能并注入可用 API Key。"""
    monkeypatch.setattr(ai_service, "_get_api_key", lambda: "test-api-key")
    return monkeypatch


async def _enable_ai(db_session) -> None:
    await ai_service.update_ai_feature_config(db_session, {"enabled": True})


# ---------------------------------------------------------------------------
# 正常路径（mock 固定文案）
# ---------------------------------------------------------------------------
async def test_item_description_returns_mocked_text(client, db_session, ai_ready):
    """物品描述润色：返回模型文案，且 prompt 携带标题与分类。"""
    await _enable_ai(db_session)
    captured = {}

    async def _fake_gemini(prompt, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return "九成新闲置自行车，校内面交，诚心转让。"

    ai_ready.setattr(ai_service, "_call_gemini", _fake_gemini)
    tokens = register_login(client, "ai_desc_user")

    r = client.post(
        "/api/ai/item-description",
        json={"title": "闲置自行车", "category": "交通工具"},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    assert r.json()["data"]["text"] == "九成新闲置自行车，校内面交，诚心转让。"
    assert "闲置自行车" in captured["prompt"]
    assert "交通工具" in captured["prompt"]


async def test_course_summary_returns_mocked_text(client, db_session, ai_ready):
    """课程评价汇总：多条评价合并进 prompt，返回汇总文案。"""
    await _enable_ai(db_session)
    captured = {}

    async def _fake_gemini(prompt, **kwargs):
        captured["prompt"] = prompt
        return "该课程讲解清晰，作业量适中，给分友好。"

    ai_ready.setattr(ai_service, "_call_gemini", _fake_gemini)
    tokens = register_login(client, "ai_sum_user")

    r = client.post(
        "/api/ai/course-summary",
        json={"reviewTexts": ["老师讲得好", "作业不多", "给分高"]},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    assert "给分" in r.json()["data"]["text"]
    for text in ("老师讲得好", "作业不多", "给分高"):
        assert text in captured["prompt"]


async def test_course_summary_rejects_empty_reviews(client, db_session, ai_ready):
    """无有效评价 → 业务错误（不浪费一次模型调用）。"""
    await _enable_ai(db_session)
    called = {"n": 0}

    async def _fake_gemini(prompt, **kwargs):
        called["n"] += 1
        return "不应被调用"

    ai_ready.setattr(ai_service, "_call_gemini", _fake_gemini)
    tokens = register_login(client, "ai_empty_user")

    r = client.post(
        "/api/ai/course-summary",
        json={"reviewTexts": ["", "   "]},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.json()["code"] != 0
    assert called["n"] == 0


# ---------------------------------------------------------------------------
# 降级与开关
# ---------------------------------------------------------------------------
async def test_upstream_failure_degrades_to_business_error(client, db_session, ai_ready):
    """上游故障 → 返回业务错误码，且**不返回任何假文案**。"""
    await _enable_ai(db_session)

    async def _boom(prompt, **kwargs):
        raise BizError(ErrorCode.INTERNAL, "AI 服务连接失败，请稍后重试")

    ai_ready.setattr(ai_service, "_call_gemini", _boom)
    tokens = register_login(client, "ai_boom_user")

    r = client.post(
        "/api/ai/item-description",
        json={"title": "台灯", "category": "日用百货"},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.json()["code"] == ErrorCode.INTERNAL
    assert r.json()["data"] is None


async def test_ai_disabled_returns_forbidden(client, db_session, ai_ready):
    """功能开关关闭 → 40300，且不会调用模型。"""
    await ai_service.update_ai_feature_config(db_session, {"enabled": False})
    called = {"n": 0}

    async def _fake(prompt, **kwargs):
        called["n"] += 1
        return "不应返回"

    ai_ready.setattr(ai_service, "_call_gemini", _fake)
    tokens = register_login(client, "ai_off_user")

    r = client.post(
        "/api/ai/item-description",
        json={"title": "台灯", "category": "日用百货"},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.json()["code"] == ErrorCode.FORBIDDEN
    assert called["n"] == 0


async def test_ai_status_reflects_switch(client, db_session, ai_ready):
    """公开状态端点如实反映开关与 Key 配置状态。"""
    await _enable_ai(db_session)
    r = client.get("/api/ai/status")
    assert r.status_code == 200 and r.json()["code"] == 0
    data = r.json()["data"]
    assert data["enabled"] is True
    assert data["available"] is True

    await ai_service.update_ai_feature_config(db_session, {"enabled": False})
    off = client.get("/api/ai/status")
    assert off.json()["data"]["enabled"] is False
    assert off.json()["data"]["available"] is False


async def test_ai_endpoints_require_authentication(client, db_session):
    """未登录调用 AI 生成接口 → 401。"""
    await _enable_ai(db_session)
    r = client.post(
        "/api/ai/item-description", json={"title": "台灯", "category": "日用百货"}
    )
    assert r.status_code == 401

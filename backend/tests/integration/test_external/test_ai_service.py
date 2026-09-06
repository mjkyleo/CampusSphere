"""AI 服务集成测试：**mock 文案 + 三层降级 + 模型链 + 熔断 + 开关**。

策略：
* 用 ``monkeypatch`` 替换 ``app.modules.ai.service._call_llm``，返回固定文案，
  验证**请求参数组装**与**响应透传**；
* 让被 mock 的函数抛 ``LLMError``，验证上游故障时的**降级行为**：
  - 可降级能力（greeting / moderation）→ 模板或规则引擎，**绝不 5xx**；
  - 不可降级能力（润色 / 画像 / 灵感）→ 业务错误码，**绝不能返回假数据**；
* 模型链与熔断器直接对 ``_call_llm`` 做白盒测试（替换 ``OpenAICompatibleClient``）。

注意 mock 点选在 ``_call_llm`` 而非 HTTP 层：既避免真实外网调用，
又能覆盖到"配置校验 → prompt 组装 → 结果返回"的完整业务链路。
"""

from __future__ import annotations

import pytest
from helpers import auth_header, register_login

import app.modules.ai.service as ai_service
from app.core.exceptions import BizError, ErrorCode
from app.modules.ai.provider import LLMError

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _clean_breaker():
    """熔断器是进程级状态，必须逐用例重置，避免相互污染。"""
    ai_service.reset_breaker()
    yield
    ai_service.reset_breaker()


@pytest.fixture
def ai_ready(monkeypatch):
    """开启 AI 功能并注入可用 API Key。"""
    monkeypatch.setattr(ai_service, "_get_api_key", lambda: "test-api-key")
    return monkeypatch


@pytest.fixture
def ai_no_key(monkeypatch):
    """模拟**未配置** API Key 的运行态。"""
    monkeypatch.setattr(ai_service, "_get_api_key", lambda: "")
    return monkeypatch


async def _enable_ai(db_session) -> None:
    await ai_service.update_ai_feature_config(db_session, {"enabled": True})


def _joined(captured: dict) -> str:
    """把 messages 拼成一段文本，便于断言 prompt 内容。"""
    return "".join(m["content"] for m in captured.get("messages", []))


def _fake_llm(captured: dict | None = None, text: str = "ok"):
    async def _f(messages, **kwargs):
        if captured is not None:
            captured["messages"] = messages
            captured["kwargs"] = kwargs
        return text
    return _f


# ---------------------------------------------------------------------------
# 正常路径（mock 固定文案）
# ---------------------------------------------------------------------------
async def test_item_description_returns_mocked_text(client, db_session, ai_ready):
    """物品描述润色：返回模型文案，且 prompt 携带标题与分类。"""
    await _enable_ai(db_session)
    captured: dict = {}
    ai_ready.setattr(
        ai_service, "_call_llm",
        _fake_llm(captured, "九成新闲置自行车，校内面交，诚心转让。"),
    )
    tokens = register_login(client, "ai_desc_user")

    r = client.post(
        "/api/ai/item-description",
        json={"title": "闲置自行车", "category": "交通工具"},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    assert r.json()["data"]["text"] == "九成新闲置自行车，校内面交，诚心转让。"
    prompt = _joined(captured)
    assert "闲置自行车" in prompt and "交通工具" in prompt


async def test_course_summary_returns_mocked_text(client, db_session, ai_ready):
    """课程评价汇总：多条评价合并进 prompt，返回汇总文案。"""
    await _enable_ai(db_session)
    captured: dict = {}
    ai_ready.setattr(
        ai_service, "_call_llm",
        _fake_llm(captured, "该课程讲解清晰，作业量适中，给分友好。"),
    )
    tokens = register_login(client, "ai_sum_user")

    r = client.post(
        "/api/ai/course-summary",
        json={"reviewTexts": ["老师讲得好", "作业不多", "给分高"]},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    assert "给分" in r.json()["data"]["text"]
    prompt = _joined(captured)
    for text in ("老师讲得好", "作业不多", "给分高"):
        assert text in prompt


async def test_course_summary_rejects_empty_reviews(client, db_session, ai_ready):
    """无有效评价 → 业务错误（不浪费一次模型调用）。"""
    await _enable_ai(db_session)
    called = {"n": 0}

    async def _fake(messages, **kwargs):
        called["n"] += 1
        return "不应被调用"

    ai_ready.setattr(ai_service, "_call_llm", _fake)
    tokens = register_login(client, "ai_empty_user")

    r = client.post(
        "/api/ai/course-summary",
        json={"reviewTexts": ["", "   "]},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.json()["code"] != 0
    assert called["n"] == 0


# ---------------------------------------------------------------------------
# 不可降级能力：失败即友好错误，绝不返回假数据
# ---------------------------------------------------------------------------
async def test_upstream_failure_degrades_to_business_error(client, db_session, ai_ready):
    """上游故障 → 返回业务错误码，且**不返回任何假文案**。"""
    await _enable_ai(db_session)

    async def _boom(messages, **kwargs):
        raise LLMError("http 500")

    ai_ready.setattr(ai_service, "_call_llm", _boom)
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

    async def _fake(messages, **kwargs):
        called["n"] += 1
        return "不应返回"

    ai_ready.setattr(ai_service, "_call_llm", _fake)
    tokens = register_login(client, "ai_off_user")

    r = client.post(
        "/api/ai/item-description",
        json={"title": "台灯", "category": "日用百货"},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.json()["code"] == ErrorCode.FORBIDDEN
    assert called["n"] == 0


# ---------------------------------------------------------------------------
# 首页问候：唯一可降级能力（模板兜底，永不阻塞）
# ---------------------------------------------------------------------------
async def test_greeting_returns_llm_text(client, db_session, ai_ready):
    """问候：正常返回模型文案，prompt 携带采集信息与表达手法。"""
    await _enable_ai(db_session)
    captured: dict = {}
    ai_ready.setattr(
        ai_service, "_call_llm",
        _fake_llm(captured, '{"text":"先把最难的那门啃下来。","emoji":"🌙"}'),
    )
    tokens = register_login(client, "ai_greet_user")

    r = client.post(
        "/api/ai/greeting",
        json={"mood": "sprint", "focus": "study", "clientSeed": "seed-1"},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["source"] == "llm"
    assert data["text"] == "先把最难的那门啃下来。"
    assert data["emoji"] == "🌙"
    prompt = _joined(captured)
    assert "冲刺备战" in prompt and "课业" in prompt and "表达手法" in prompt


async def test_greeting_degrades_to_template_on_failure(client, db_session, ai_ready):
    """上游故障 → 问候降级为模板（200 + source=fallback），首页不报错。"""
    await _enable_ai(db_session)

    async def _boom(messages, **kwargs):
        raise LLMError("http 500")

    ai_ready.setattr(ai_service, "_call_llm", _boom)
    tokens = register_login(client, "ai_greet_fb")

    r = client.post(
        "/api/ai/greeting",
        json={"mood": "tired", "focus": ""},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["source"] == "fallback"
    assert data["text"]


async def test_greeting_works_without_api_key(client, db_session, ai_no_key):
    """未配置 API Key → 问候仍返回模板，主流程零阻塞。"""
    await _enable_ai(db_session)
    tokens = register_login(client, "ai_greet_nokey")

    r = client.post(
        "/api/ai/greeting", json={}, headers=auth_header(tokens["access_token"])
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["source"] == "fallback"
    assert data["text"]


async def test_greeting_invalid_enum_is_normalized(client, db_session, ai_no_key):
    """mood/focus 非法值走白名单归一化，不被拼进 prompt（防注入）。"""
    await _enable_ai(db_session)
    tokens = register_login(client, "ai_greet_enum")

    r = client.post(
        "/api/ai/greeting",
        json={"mood": "<script>alert(1)</script>", "focus": "DROP TABLE"},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["mood"] == "" and data["focus"] == ""


async def test_greeting_cache_and_regenerate(client, db_session, ai_ready):
    """同参数复用当日缓存；regenerate 产生新 attempt 并再次调用模型。"""
    await _enable_ai(db_session)
    called = {"n": 0}

    async def _fake(messages, **kwargs):
        called["n"] += 1
        return '{"text":"今日问候","emoji":"☀️"}'

    ai_ready.setattr(ai_service, "_call_llm", _fake)
    tokens = register_login(client, "ai_greet_cache")
    headers = auth_header(tokens["access_token"])
    payload = {"mood": "steady", "focus": "study", "clientSeed": "s"}

    first = client.post("/api/ai/greeting", json=payload, headers=headers)
    assert first.json()["data"]["attempt"] == 0
    assert called["n"] == 1

    again = client.post("/api/ai/greeting", json=payload, headers=headers)
    assert again.json()["data"]["text"] == first.json()["data"]["text"]
    assert called["n"] == 1, "同参数应命中当日缓存，不应重复调用模型"

    regen = client.post(
        "/api/ai/greeting", json={**payload, "regenerate": True}, headers=headers
    )
    assert regen.json()["data"]["attempt"] == 1
    assert called["n"] == 2


# ---------------------------------------------------------------------------
# 内容预审：降级到规则引擎
# ---------------------------------------------------------------------------
async def test_moderation_degrades_to_rule_engine(client, db_session, ai_ready):
    """LLM 不可用 → 分类降级为规则引擎，保证不阻塞发布。"""
    await _enable_ai(db_session)

    async def _boom(messages, **kwargs):
        raise LLMError("http 500")

    ai_ready.setattr(ai_service, "_call_llm", _boom)
    tokens = register_login(client, "ai_mod_user")

    r = client.post(
        "/api/ai/categorize",
        json={"content": "转让一辆闲置自行车，低价出，校内面交"},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["source"] == "rule"
    assert data["category"] == "二手交易"
    assert data["isSafe"] is True


async def test_moderation_rule_flags_unsafe_content(client, db_session, ai_no_key):
    """敏感词命中 → isSafe=False（规则引擎独立于 LLM 生效）。"""
    await _enable_ai(db_session)
    tokens = register_login(client, "ai_mod_bad")

    r = client.post(
        "/api/ai/categorize",
        json={"content": "有偿代考，四六级包过"},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.json()["code"] == 0
    assert r.json()["data"]["isSafe"] is False


# ---------------------------------------------------------------------------
# 状态端点：能力级粒度
# ---------------------------------------------------------------------------
async def test_ai_status_reflects_switch(client, db_session, ai_ready):
    """公开状态端点如实反映开关与 Key 配置状态，并给出能力级明细。"""
    await _enable_ai(db_session)
    r = client.get("/api/ai/status")
    assert r.status_code == 200 and r.json()["code"] == 0
    data = r.json()["data"]
    assert data["enabled"] is True
    assert data["available"] is True
    assert "greeting" in data["capabilities"]
    assert data["capabilities"]["greeting"]["available"] is True

    await ai_service.update_ai_feature_config(db_session, {"enabled": False})
    off = client.get("/api/ai/status")
    assert off.json()["data"]["enabled"] is False
    assert off.json()["data"]["available"] is False
    assert off.json()["data"]["capabilities"]["greeting"]["available"] is False


async def test_ai_status_reports_missing_key(client, db_session, ai_no_key):
    """开关开但无 Key → available=False，前端据此隐藏全部 AI 入口。"""
    await _enable_ai(db_session)
    data = client.get("/api/ai/status").json()["data"]
    assert data["enabled"] is True
    assert data["available"] is False
    assert "AI_API_KEY" in data["message"]


async def test_ai_endpoints_require_authentication(client, db_session):
    """未登录调用 AI 生成接口 → 401。"""
    await _enable_ai(db_session)
    r = client.post(
        "/api/ai/item-description", json={"title": "台灯", "category": "日用百货"}
    )
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# L2 模型链与熔断器（白盒）
# ---------------------------------------------------------------------------
async def test_call_llm_falls_back_to_next_model(ai_ready):
    """主模型失败 → 自动尝试 fallback_models 中的下一个模型。"""
    cfg = ai_service._static_runtime()
    cfg["primary_model"] = "bad-model"
    cfg["fallback_models"] = ["backup-model"]
    cfg["max_retries"] = 0
    calls: list[str] = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def chat(self, *, model, **kwargs):
            calls.append(model)
            if model == "bad-model":
                raise LLMError("http 500")
            return "来自备用模型"

    ai_ready.setattr(ai_service, "OpenAICompatibleClient", FakeClient)

    out = await ai_service._call_llm([{"role": "user", "content": "hi"}], cfg=cfg)
    assert out == "来自备用模型"
    assert calls == ["bad-model", "backup-model"]


async def test_call_llm_skips_retry_on_fatal_error(ai_ready):
    """4xx（非 429）属于致命错误：不重试、不换模型，快速失败。"""
    cfg = ai_service._static_runtime()
    cfg["primary_model"] = "m1"
    cfg["fallback_models"] = ["m2"]
    cfg["max_retries"] = 2
    calls: list[str] = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def chat(self, *, model, **kwargs):
            calls.append(model)
            raise LLMError("http 401")

    ai_ready.setattr(ai_service, "OpenAICompatibleClient", FakeClient)

    with pytest.raises(LLMError):
        await ai_service._call_llm([{"role": "user", "content": "hi"}], cfg=cfg)
    assert calls == ["m1"], "致命 4xx 不应触发重试与模型切换"


async def test_circuit_breaker_opens_after_threshold(ai_ready):
    """连续失败达阈值 → 熔断，冷却期内直接短路，不再打上游。"""
    cfg = ai_service._static_runtime()
    cfg["primary_model"] = "m1"
    cfg["fallback_models"] = []
    cfg["max_retries"] = 0
    cfg["cb_threshold"] = 2
    cfg["cb_cooldown"] = 60

    class BoomClient:
        def __init__(self, *args, **kwargs):
            pass

        async def chat(self, **kwargs):
            raise LLMError("http 500")

    ai_ready.setattr(ai_service, "OpenAICompatibleClient", BoomClient)

    for _ in range(2):
        with pytest.raises(LLMError):
            await ai_service._call_llm([{"role": "user", "content": "x"}], cfg=cfg)

    assert ai_service.breaker_open() is True

    with pytest.raises(LLMError) as exc:
        await ai_service._call_llm([{"role": "user", "content": "x"}], cfg=cfg)
    assert "circuit open" in str(exc.value)


async def test_breaker_open_makes_greeting_use_template(client, db_session, ai_ready):
    """熔断中 → 问候直接走模板，不触网。"""
    await _enable_ai(db_session)
    called = {"n": 0}

    async def _fake(messages, **kwargs):
        called["n"] += 1
        return "不应被调用"

    ai_ready.setattr(ai_service, "_call_llm", _fake)
    ai_service._breaker["open_until"] = ai_service.time.monotonic() + 60
    tokens = register_login(client, "ai_greet_breaker")

    r = client.post(
        "/api/ai/greeting", json={"mood": "steady"},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.json()["code"] == 0
    assert r.json()["data"]["source"] == "fallback"
    assert called["n"] == 0


# ---------------------------------------------------------------------------
# 模板库
# ---------------------------------------------------------------------------
def test_greeting_templates_vary_by_seed():
    """不同种子应产出不同句子（保证"每次启动不同"）。"""
    from app.modules.ai.templates import pick_greeting_template

    seen = {
        pick_greeting_template(mood="steady", period="morning", seed=s)[0]
        for s in range(12)
    }
    assert len(seen) >= 6, f"模板多样性不足：{len(seen)}"


def test_greeting_template_respects_period():
    """时段应体现在文案中。"""
    from app.modules.ai.templates import pick_greeting_template

    text, emoji = pick_greeting_template(mood="tired", period="night", seed=0)
    assert "夜" in text or "晚" in text or "睡" in text
    assert emoji

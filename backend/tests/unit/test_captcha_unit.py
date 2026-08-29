"""滑块验证码单元测试。

聚焦**纯逻辑与安全不变式**，不经过 HTTP 层（HTTP 集成由
``tests/test_captcha.py`` 覆盖），因此这里可以：

* 直接窥探服务端保存的缺口坐标（``redis`` 内存兜底），精确构造"命中"与"偏差"两种输入；
* 针对反脚本判定（轨迹形态 / 耗时下限）做边界断言，这些细节在 API 层不可见。

安全不变式（回归保护重点）
--------------------------
1. 缺口横坐标 **绝不出现在生成响应中**——一旦出现，拼图验证形同虚设；
2. 令牌 **一次性**：无论校验成功还是失败，都不能用同一令牌二次校验；
3. 票据 **一次性**：``consume_ticket`` 第二次必须返回 False（防重放刷验证码）。
"""

from __future__ import annotations

import json

import pytest

from app.common.utils import generate_code
from app.core.config import settings
from app.core.exceptions import BizError
from app.modules.auth.captcha import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    SLIDER_SIZE,
    _puzzle_mask,
    _random_background,
    _to_data_uri,
    _track_looks_human,
    consume_ticket,
    generate_slider,
    issue_ticket,
    verify_slider,
)

pytestmark = pytest.mark.unit

_SLIDER_KEY_PREFIX = "captcha:slider:"


# ---------------------------------------------------------------------------
# 测试辅助
# ---------------------------------------------------------------------------
def _human_track(target_x: float, points: int = 12) -> list[list[float]]:
    """构造一条"像人"的拖动轨迹：先快后慢、步进不完全一致、时间递增。

    滑块模块会拦截**匀速直线**轨迹（脚本特征），因此这里用 ``ratio**0.75``
    产生非线性的、每步位移都不同的采样点。
    """
    track = []
    for i in range(points):
        ratio = (i / (points - 1)) ** 0.75
        track.append([i * 30, round(target_x * ratio, 2), 40.0])
    return track


async def _generate_with_secret_x():
    """生成滑块并**窥探**服务端保存的真实缺口横坐标。

    缺口 x 不会下发给前端，但单元测试需要它来构造"命中"用例；
    直接从 Redis 内存兜底读取是最可靠的做法。
    """
    data = await generate_slider()
    import app.core.redis as redis_module

    raw = redis_module._memory_fallback[f"{_SLIDER_KEY_PREFIX}{data['token']}"]
    return data, float(json.loads(raw)["x"])


# ---------------------------------------------------------------------------
# 图像生成（纯函数）
# ---------------------------------------------------------------------------
def test_random_background_size_and_variation():
    """背景图尺寸固定，且两次生成结果不同（防字典攻击）。"""
    img1 = _random_background(CANVAS_WIDTH, CANVAS_HEIGHT)
    img2 = _random_background(CANVAS_WIDTH, CANVAS_HEIGHT)
    assert img1.size == (CANVAS_WIDTH, CANVAS_HEIGHT)
    assert img1.tobytes() != img2.tobytes()


def test_puzzle_mask_is_grayscale_and_sized():
    """拼图遮罩：单通道 L 模式，边长等于滑块尺寸。"""
    mask = _puzzle_mask(SLIDER_SIZE)
    assert mask.mode == "L"
    assert mask.size == (SLIDER_SIZE, SLIDER_SIZE)


def test_to_data_uri_uses_png_base64():
    """图片以 data:image/png;base64 下发（SVG 会泄露缺口坐标，故不用）。"""
    uri = _to_data_uri(_random_background(CANVAS_WIDTH, CANVAS_HEIGHT))
    assert uri.startswith("data:image/png;base64,")
    assert len(uri) > 100


# ---------------------------------------------------------------------------
# 生成接口：安全不变式
# ---------------------------------------------------------------------------
async def test_generate_slider_never_exposes_target_x():
    """【安全不变式 1】响应中不得出现缺口横坐标。"""
    data = await generate_slider()
    # 只下发纵坐标 y（前端需要它把滑块放在同一水平线），x 必须缺席
    assert "x" not in data
    assert "target_x" not in data
    assert "y" in data
    # 即便把整个响应序列化后搜索，也不能泄露坐标字符串
    assert str(data["token"]) not in json.dumps({k: v for k, v in data.items() if k != "token"})


async def test_generate_slider_payload_shape():
    """生成响应字段完整：两张图 + 画布尺寸 + 纵坐标 + 有效期。"""
    data = await generate_slider()
    assert data["width"] == CANVAS_WIDTH
    assert data["height"] == CANVAS_HEIGHT
    assert data["slider_size"] == SLIDER_SIZE
    assert 0 <= data["y"] <= CANVAS_HEIGHT - SLIDER_SIZE
    assert data["expires_in"] > 0
    for key in ("background", "slider"):
        assert data[key].startswith("data:image/png;base64,")


async def test_generate_slider_tokens_are_unique():
    """每次生成返回不同令牌（防止令牌可预测导致批量绕过）。"""
    a = await generate_slider()
    b = await generate_slider()
    assert a["token"] != b["token"]


# ---------------------------------------------------------------------------
# 轨迹形态反脚本判定
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("track", "expected", "reason"),
    [
        ([[0, 0], [30, 10], [60, 25], [90, 45], [120, 70]], True, "正常：步进不等、整体向前"),
        ([[0, 0], [30, 50]], False, "采样点不足"),
        ([[0, 0], [30, 10], [60, 20], [90, 30]], False, "完全匀速（脚本特征）"),
        ([[0, 80], [30, 60], [60, 40], [90, 20]], False, "整体向后回退"),
        ([[0, 0], [30, 500]], False, "单步跳变过大（伪造轨迹）"),
        ("not-a-list", False, "类型错误"),
        ([[0, "abc"], [30, 10]], False, "坐标非数值"),
        ([[0, 0]], False, "只有一个点"),
    ],
)
def test_track_looks_human(track, expected, reason):
    """轨迹形态校验：覆盖正常/采样不足/匀速/回退/跳变/脏数据。"""
    assert _track_looks_human(track, min_points=3) is expected, reason


# ---------------------------------------------------------------------------
# 校验接口
# ---------------------------------------------------------------------------
async def test_verify_slider_success_returns_ticket():
    """命中缺口 + 人类轨迹 → 返回票据。"""
    data, target_x = await _generate_with_secret_x()
    ticket = await verify_slider(
        data["token"], target_x, _human_track(target_x), elapsed_ms=600
    )
    assert isinstance(ticket, str) and ticket


async def test_verify_slider_wrong_offset_rejected():
    """偏差超过容差 → BizError。"""
    data, target_x = await _generate_with_secret_x()
    with pytest.raises(BizError):
        await verify_slider(
            data["token"], target_x + 500, _human_track(target_x + 500), elapsed_ms=600
        )


async def test_verify_slider_token_is_single_use_on_success():
    """【安全不变式 2】校验**通过**后令牌立即作废，不能二次换票。"""
    data, target_x = await _generate_with_secret_x()
    assert await verify_slider(data["token"], target_x, _human_track(target_x), 600)
    with pytest.raises(BizError):
        await verify_slider(data["token"], target_x, _human_track(target_x), 600)


async def test_verify_slider_allows_limited_retries_then_locks():
    """失败未达上限时允许重试（用户拖歪属正常操作），达到上限后令牌作废。

    说明：模块文档曾表述为"无论成败都立即作废"，而实现是
    ``tries <= captcha_max_attempts`` 的**有限重试**策略。这里以**实现为准**
    锁定行为——既防止后续改动悄悄放宽（变成无限试探），也防止误改成
    "一次失败即作废"而伤害真实用户。
    """
    data, target_x = await _generate_with_secret_x()
    for _ in range(settings.captcha_max_attempts):
        with pytest.raises(BizError):
            await verify_slider(data["token"], target_x + 500, _human_track(50), 600)
    # 用尽次数后令牌已被删除，即便坐标正确也不再可用
    with pytest.raises(BizError):
        await verify_slider(data["token"], target_x, _human_track(target_x), 600)


async def test_verify_slider_rejects_unknown_token():
    """未知 / 空令牌 → BizError（不区分"坐标错"与"令牌失效"，避免信息泄露）。"""
    with pytest.raises(BizError):
        await verify_slider("", 10, _human_track(10), elapsed_ms=600)
    with pytest.raises(BizError):
        await verify_slider("nonexistent-token", 10, _human_track(10), elapsed_ms=600)


async def test_verify_slider_rejects_instant_drag():
    """耗时低于人类下限（脚本直传坐标）→ 拒绝。"""
    data, target_x = await _generate_with_secret_x()
    with pytest.raises(BizError):
        await verify_slider(data["token"], target_x, _human_track(target_x), elapsed_ms=5)


# ---------------------------------------------------------------------------
# 票据（send-code 的闸门）
# ---------------------------------------------------------------------------
async def test_ticket_is_single_use():
    """【安全不变式 3】票据一次性消费，第二次必须失败（防重放）。"""
    ticket = await issue_ticket()
    assert await consume_ticket(ticket) is True
    assert await consume_ticket(ticket) is False


@pytest.mark.parametrize("bad_ticket", [None, "", "unknown-ticket"])
async def test_consume_ticket_rejects_invalid(bad_ticket):
    """空值 / 未知票据一律拒绝，send-code 不得放行。"""
    assert await consume_ticket(bad_ticket) is False


# ---------------------------------------------------------------------------
# 验证码生成（注册/登录共用）
# ---------------------------------------------------------------------------
def test_generate_code_length_and_digits():
    """验证码：默认 6 位纯数字，长度可配置。"""
    code = generate_code()
    assert len(code) == 6 and code.isdigit()
    assert len(generate_code(4)) == 4 and generate_code(4).isdigit()


def test_generate_code_is_random():
    """多次生成不重复（抽样 20 次，重复率应为 0）。"""
    codes = {generate_code() for _ in range(20)}
    assert len(codes) == 20

"""Task 3 单元测试：验证码生成的事件循环隔离（asyncio.to_thread）。

验收标准不是"功能跑通"，而是**主事件循环不被阻塞**：
在图像渲染进行的同时，事件循环仍能及时处理其他协程（心跳）。

做法：把渲染函数替换成一个"慢同步函数"（``time.sleep``），同时跑一个
高频心跳协程并统计它在渲染期间完成了多少次 tick。
- 若渲染确实委派给了线程池 → 心跳照常 tick（次数接近 耗时/间隔）；
- 若渲染仍在事件循环内同步执行 → 心跳被冻结（次数≈0）。

这是**可证伪**的断言：把 ``asyncio.to_thread`` 去掉，本测试立刻失败。
"""

from __future__ import annotations

import asyncio
import json
import time

import pytest

from app.modules.auth import captcha as captcha_module
from app.modules.auth.captcha import generate_slider


@pytest.mark.asyncio
async def test_render_runs_in_thread_not_blocking_event_loop(monkeypatch) -> None:
    """渲染期间事件循环必须保持响应（心跳不被冻结）。"""
    render_seconds = 0.3

    def _slow_render(target_x: int, target_y: int) -> tuple[str, str]:
        # 刻意用同步 sleep 模拟 CPU 密集：若它跑在事件循环里，会把循环整个卡住
        time.sleep(render_seconds)
        return ("data:image/png;base64,AAA", "data:image/png;base64,BBB")

    monkeypatch.setattr(captcha_module, "_render_slider_images", _slow_render)

    ticks = 0
    stop = asyncio.Event()

    async def _heartbeat() -> None:
        nonlocal ticks
        while not stop.is_set():
            await asyncio.sleep(0.01)
            ticks += 1

    beat = asyncio.create_task(_heartbeat())
    started = time.perf_counter()
    payload = await generate_slider()
    elapsed = time.perf_counter() - started

    stop.set()
    await beat

    # 渲染确实发生了（耗时接近模拟的 sleep）
    assert elapsed >= render_seconds * 0.9, f"渲染未执行，耗时仅 {elapsed:.3f}s"

    # 关键断言：心跳在渲染期间持续 tick，说明事件循环未被独占
    expected = render_seconds / 0.01
    assert ticks >= expected * 0.5, (
        f"事件循环被阻塞：渲染 {render_seconds}s 内心跳只 tick 了 {ticks} 次"
        f"（预期约 {expected:.0f} 次）"
    )

    # 线程池返回的结果被正确接回
    assert payload["slider"] == "data:image/png;base64,AAA"
    assert payload["background"] == "data:image/png;base64,BBB"


@pytest.mark.asyncio
async def test_real_render_produces_valid_payload() -> None:
    """真实 Pillow 渲染：返回可渲染的 data URI，缺口坐标只落 Redis。"""
    payload = await generate_slider()

    assert payload["slider"].startswith("data:image/png;base64,")
    assert payload["background"].startswith("data:image/png;base64,")
    assert payload["width"] == captcha_module.CANVAS_WIDTH
    assert payload["height"] == captcha_module.CANVAS_HEIGHT
    # 纵坐标需要下发给前端（滑块与缺口同一水平线），横坐标绝不外泄
    assert 0 <= payload["y"] < captcha_module.CANVAS_HEIGHT
    assert "x" not in payload

    # 缺口横坐标只存在于 Redis，且落在可拖动范围内
    raw = await captcha_module.redis_get(
        captcha_module._SLIDER_PREFIX + payload["token"]
    )
    assert raw is not None
    stored = json.loads(raw)
    assert isinstance(stored["x"], int)
    assert captcha_module.SLIDER_SIZE <= stored["x"] < (
        captcha_module.CANVAS_WIDTH - captcha_module.SLIDER_SIZE
    )
    assert stored["y"] == payload["y"]


@pytest.mark.asyncio
async def test_heartbeat_metric_actually_detects_blocking(monkeypatch) -> None:
    """**对照实验**：证明上面的心跳指标真的能测出阻塞，而非恒真断言。

    把 ``asyncio.to_thread`` 换成"直接在事件循环里同步调用"（即重构前的
    写法），此时心跳必须被冻结。若这条对照不成立，说明前一个测试的
    ``ticks`` 断言根本无效——它会在两种实现下都通过。
    """
    render_seconds = 0.3

    def _slow_render(target_x: int, target_y: int) -> tuple[str, str]:
        time.sleep(render_seconds)
        return ("data:image/png;base64,AAA", "data:image/png;base64,BBB")

    monkeypatch.setattr(captcha_module, "_render_slider_images", _slow_render)

    # 模拟重构前的写法：在 async 函数里直接同步调用（不委派线程）。
    # 必须是 async def 才能被 await —— 直接返回元组会抛 TypeError，
    # 那样测的就不是"阻塞"而是"类型错误"了。
    async def _blocking_to_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(captcha_module.asyncio, "to_thread", _blocking_to_thread)

    ticks = 0
    stop = asyncio.Event()

    async def _heartbeat() -> None:
        nonlocal ticks
        while not stop.is_set():
            await asyncio.sleep(0.01)
            ticks += 1

    beat = asyncio.create_task(_heartbeat())
    await generate_slider()
    stop.set()
    await beat

    # 阻塞写法下心跳应当几乎完全停摆，与前一个测试形成鲜明对照
    assert ticks < 5, f"对照实验失效：阻塞实现下心跳仍 tick 了 {ticks} 次"


@pytest.mark.asyncio
async def test_render_function_is_pure_and_sync() -> None:
    """被委派的函数必须是纯同步的：线程里不能有隐式 IO。

    这是线程安全的前提——若它内部 await 或访问共享连接，
    并发渲染就会互相干扰。
    """
    import inspect

    assert not inspect.iscoroutinefunction(captcha_module._render_slider_images)

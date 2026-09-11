"""Task 4 单元测试：school.yaml 配置热更新（Redis Pub/Sub + 原地刷新）。

覆盖点：
1. 收到 reload 消息后 **原地**刷新 Settings 单例（引用不变，值更新）。
2. Redis 不可用时优雅降级：不抛异常、不阻断启动。
3. 监听器自愈：单条消息处理失败（如 YAML 写错）不终止监听循环。
4. start/stop 幂等，关闭时不泄漏后台任务。

为何强调"原地刷新"：``settings`` 被数十个模块在导入期以
``from app.core.config import settings`` 绑定。若热更新重建了对象，
那些模块仍持有旧引用 —— 热更新会**静默失效**，这是最危险的一类 bug。
"""

from __future__ import annotations

import asyncio

import pytest

from app.core import config_reload as reloader
from app.core.config import settings


@pytest.mark.asyncio
async def test_reload_updates_settings_in_place(monkeypatch, tmp_path) -> None:
    """核心断言：刷新后**对象仍是同一个**，但值已更新。

    测试隔离：本用例会真实改动全局 ``settings`` 单例，必须显式登记还原，
    否则后续用例会读到被污染的 ``school_name`` —— 这类"用例间串味"的
    偶发失败极难排查。
    """
    # 准备一份临时 YAML，先写 A 再改成 B
    yaml_file = tmp_path / "school.yaml"
    yaml_file.write_text("school_name: 甲大学\n", encoding="utf-8")
    monkeypatch.setenv("SCHOOL_CONFIG_PATH", str(yaml_file))

    # 登记还原：monkeypatch 在 teardown 时把这两个值恢复原状
    monkeypatch.setattr(settings, "school_name", settings.school_name)

    await reloader.reload_settings(reason="test:initial")
    assert settings.school_name == "甲大学"

    original = settings  # 记录引用，刷新后必须是同一个对象

    yaml_file.write_text("school_name: 乙大学\n", encoding="utf-8")
    await reloader.reload_settings(reason="test:changed")

    # 值已更新 **且** 引用未变 —— 依赖 settings 的模块自动看到新值
    assert settings.school_name == "乙大学"
    assert settings is original


@pytest.mark.asyncio
async def test_reload_uses_thread_for_file_io(monkeypatch) -> None:
    """YAML 读取是同步 IO，必须委派线程，避免热更新反过来造成循环抖动。"""
    calls: list[str] = []

    # 打在类上后调用会成为绑定方法，需显式接收 self
    def _fake_load(self) -> None:
        calls.append("load")

    async def _spy_to_thread(func, /, *args, **kwargs):
        calls.append("to_thread")
        return func(*args, **kwargs)

    # Settings 是 pydantic BaseSettings，实例上不允许 setattr 任意属性；
    # 必须打在**类**上（load_school_config 是普通方法，非 pydantic 字段）。
    monkeypatch.setattr(type(settings), "load_school_config", _fake_load)
    monkeypatch.setattr(reloader.asyncio, "to_thread", _spy_to_thread)

    await reloader.reload_settings()
    assert calls == ["to_thread", "load"]


@pytest.mark.asyncio
async def test_publish_returns_zero_instead_of_raising_when_redis_down(
    monkeypatch,
) -> None:
    """Redis 不可用：发布返回 0 并告警，绝不把异常抛给"改配置"主流程。"""

    async def _boom(channel: str, message: str) -> int:
        raise RuntimeError("redis down")

    monkeypatch.setattr(reloader, "redis_publish", _boom)
    assert await reloader.publish_config_reload(reason="test") == 0


@pytest.mark.asyncio
async def test_listener_degrades_gracefully_without_redis(monkeypatch) -> None:
    """无 Redis 时监听器不崩溃：记录警告后进入慢速重试，不影响主进程。"""
    monkeypatch.setattr(reloader, "RETRY_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(reloader, "redis_subscribe", lambda _ch: asyncio.sleep(0, None))

    warnings: list[str] = []

    class _Log:
        def warning(self, event, **kw):
            warnings.append(event)

        def info(self, event, **kw):
            pass

        def error(self, event, **kw):
            pass

    monkeypatch.setattr(reloader, "_logger", _Log())

    # 让它跑几轮重试，然后取消
    task = asyncio.create_task(reloader._listen())
    await asyncio.sleep(0.05)
    assert not task.done(), "监听器不应因 Redis 不可用而退出"
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert "config_reload_unavailable_fallback" in warnings


@pytest.mark.asyncio
async def test_single_bad_message_does_not_kill_listener(monkeypatch) -> None:
    """一条消息处理失败（如 YAML 语法错误）后，监听器必须继续工作。"""
    monkeypatch.setattr(reloader, "RETRY_INTERVAL_SECONDS", 0.01)

    messages = [
        {"type": "message", "data": "bad-1"},
        {"type": "message", "data": "good-2"},
        {"type": "subscribe", "data": 1},  # 非 message 类型应被忽略
    ]

    class _PubSub:
        async def listen(self):
            for m in messages:
                yield m
            # 消息发完后阻塞，模拟长连接保持。若直接返回，外层循环会立即
            # 判定"连接断开"并重连，把同一批消息重放一遍，使断言失真。
            await asyncio.Event().wait()

        async def aclose(self) -> None:
            pass

    async def _fake_subscribe(_ch):
        return _PubSub()

    monkeypatch.setattr(reloader, "redis_subscribe", _fake_subscribe)

    reload_calls: list[str] = []
    errors: list[str] = []

    async def _flaky_reload(reason: str = "") -> None:
        reload_calls.append(reason)
        if reason == "bad-1":
            raise RuntimeError("yaml syntax error")

    monkeypatch.setattr(reloader, "reload_settings", _flaky_reload)

    class _Log:
        def warning(self, event, **kw):
            pass

        def info(self, event, **kw):
            pass

        def error(self, event, **kw):
            errors.append(event)

    monkeypatch.setattr(reloader, "_logger", _Log())

    task = asyncio.create_task(reloader._listen())
    await asyncio.sleep(0.05)
    alive = not task.done()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # 失败被记录，但监听器存活（未被异常终止）
    assert "config_reload_failed" in errors
    assert alive
    # 非 message 类型的控制帧不触发刷新
    assert reload_calls == ["bad-1", "good-2"]


@pytest.mark.asyncio
async def test_start_and_stop_are_idempotent(monkeypatch) -> None:
    """重复 start 不产生多个任务；stop 可重复调用且不留残留。"""
    monkeypatch.setattr(reloader, "RETRY_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(reloader, "redis_subscribe", lambda _ch: asyncio.sleep(0, None))

    class _Log:
        def warning(self, event, **kw):
            pass

        def info(self, event, **kw):
            pass

        def error(self, event, **kw):
            pass

    monkeypatch.setattr(reloader, "_logger", _Log())

    await reloader.start_config_reloader()
    first = reloader._task
    await reloader.start_config_reloader()  # 幂等：不应新建任务
    assert reloader._task is first

    await reloader.stop_config_reloader()
    assert reloader._task is None
    await reloader.stop_config_reloader()  # 幂等：重复关闭安全
    assert reloader._task is None

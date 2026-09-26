"""WS 多实例广播修复的防回归测试（fakeredis）。

历史缺陷：``_redis_listen`` 曾用 ``redis_subscribe("conv:*")`` —— subscribe
只匹配**字面量**频道 ``"conv:*"``，永远收不到发布到 ``conv:<会话ID>`` 的消息，
多实例广播与跨实例已读回执静默失效（单实例本地直发掩盖了故障，测试全绿）。

本文件锁死三件事：
1. 模式订阅必须走 psubscribe，发布到具体频道能被 ``conv:*`` 收到（pmessage）；
2. 监听器跳过 ``origin`` 为本实例的消息（防止「本地直发 + 自身监听」重复投递）；
3. 监听器把跨实例消息投递给 recipients 中本实例在线的连接。
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

import fakeredis.aioredis
import pytest

import app.modules.message.ws as ws_module
from app.modules.message.ws import ConnectionManager, _INSTANCE_ID


class _FakeWebSocket:
    """记录收到的 payload，模拟本实例在线连接。"""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


async def _next_data_message(pubsub) -> dict:
    """跳过订阅确认帧，取下一条 pmessage 数据消息。"""
    async for message in pubsub.listen():
        if message.get("type") == "pmessage":
            return message
    raise AssertionError("pubsub closed without data message")


async def _wait_until(predicate: Callable[[], bool], timeout: float = 2.0) -> None:
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while not predicate():
        if loop.time() > deadline:
            raise TimeoutError("condition not met in time")
        await asyncio.sleep(0.02)


@pytest.mark.asyncio
async def test_pattern_subscription_receives_specific_channel_publish() -> None:
    """psubscribe("conv:*") 必须能收到发布到 conv:<id> 的消息。

    若有人把 redis_psubscribe 改回 redis_subscribe（历史上的静默故障），
    本用例会因等不到 pmessage 而超时失败。
    """
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.psubscribe("conv:*")
    try:
        await r.publish("conv:abc-123", json.dumps({"event": "message:new"}))
        message = await asyncio.wait_for(_next_data_message(pubsub), timeout=2)
        assert json.loads(message["data"])["event"] == "message:new"
    finally:
        await pubsub.aclose()
        await r.aclose()


@pytest.mark.asyncio
async def test_listener_delivers_cross_instance_message(monkeypatch) -> None:
    """跨实例消息（origin 非本实例）应投递给本实例在线的 recipients。"""
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.psubscribe("conv:*")

    async def _fake_psubscribe(_pattern: str):
        return pubsub

    monkeypatch.setattr(ws_module, "redis_psubscribe", _fake_psubscribe)

    manager = ConnectionManager()
    ws_local = _FakeWebSocket()
    manager._connections["user-1"] = {ws_local}

    task = asyncio.create_task(manager._redis_listen())
    try:
        await asyncio.sleep(0)  # 让监听任务先跑起来
        await r.publish(
            "conv:c1",
            json.dumps(
                {
                    "event": "message:new",
                    "recipients": ["user-1"],
                    "origin": "other-instance",
                }
            ),
        )
        await asyncio.wait_for(_wait_until(lambda: ws_local.sent), timeout=2)
        assert ws_local.sent[0]["event"] == "message:new"
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await pubsub.aclose()
        await r.aclose()


@pytest.mark.asyncio
async def test_listener_skips_own_origin(monkeypatch) -> None:
    """origin 为本实例的消息已由 publish() 本地直发，监听器必须跳过。"""
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.psubscribe("conv:*")

    async def _fake_psubscribe(_pattern: str):
        return pubsub

    monkeypatch.setattr(ws_module, "redis_psubscribe", _fake_psubscribe)

    manager = ConnectionManager()
    ws_local = _FakeWebSocket()
    manager._connections["user-1"] = {ws_local}

    task = asyncio.create_task(manager._redis_listen())
    try:
        await asyncio.sleep(0)
        await r.publish(
            "conv:c1",
            json.dumps(
                {
                    "event": "message:new",
                    "recipients": ["user-1"],
                    "origin": _INSTANCE_ID,
                }
            ),
        )
        # 给监听器足够的处理窗口，确认**没有**投递（若误投递，0.2s 内必然送达）
        await asyncio.sleep(0.2)
        assert ws_local.sent == []
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await pubsub.aclose()
        await r.aclose()

"""站内通知 Celery 任务单元测试。

不连数据库、不连 Redis，只验证任务体能正确构造消息并通过 ``redis_publish``
投递到 ``notify:{user_id}`` 频道。
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from app.tasks.notify import send_notify

pytestmark = pytest.mark.unit


def test_send_notify_publishes_to_user_channel(monkeypatch):
    """inapp 通知应向 ``notify:<user_id>`` 发布 JSON 消息。"""
    published = []

    async def _fake_publish(channel: str, message: str) -> int:
        published.append((channel, message))
        return 1

    monkeypatch.setattr("app.tasks.notify.redis_publish", _fake_publish)

    result = send_notify.run("user-123", "测试标题", "测试内容", channel="inapp")

    assert result == {"ok": True}
    assert len(published) == 1
    channel, raw = published[0]
    assert channel == "notify:user-123"
    payload = json.loads(raw)
    assert payload["event"] == "notify"
    assert payload["data"]["user_id"] == "user-123"
    assert payload["data"]["title"] == "测试标题"
    assert payload["data"]["content"] == "测试内容"


def test_send_notify_sms_channel_does_not_publish(monkeypatch):
    """sms 通道目前未实现，不触发 Redis 发布。"""
    published: list[tuple[str, str]] = []

    async def _fake_publish(channel: str, message: str) -> int:
        published.append((channel, message))
        return 1

    monkeypatch.setattr("app.tasks.notify.redis_publish", _fake_publish)

    result = send_notify.run("user-123", "测试标题", "测试内容", channel="sms")

    assert result == {"ok": True}
    assert published == []

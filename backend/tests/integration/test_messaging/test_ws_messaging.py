"""WebSocket 即时消息集成测试：**连接 → 发送 → 持久化 → 越权拒绝**。

既有 ``tests/test_websocket.py`` 覆盖了鉴权/心跳/广播，本文件聚焦
**消息落库与业务约束**，两者互补不重复。
"""

from __future__ import annotations

import pytest
from helpers import auth_header, register_login

pytestmark = pytest.mark.integration


def _trade_context(client, seller_name: str, buyer_name: str) -> tuple[dict, dict, dict]:
    """卖家发布 → 买家发起议价，返回 (seller, buyer, trade)。"""
    seller = register_login(client, seller_name)
    buyer = register_login(client, buyer_name)
    item = client.post(
        "/api/items",
        json={
            "title": "WS 消息测试物品",
            "description": "可议价",
            "price": 3000,
            "category": "书籍资料",
            "images": [],
        },
        headers=auth_header(seller["access_token"]),
    ).json()["data"]
    trade = client.post(
        f"/api/items/{item['id']}/trade", headers=auth_header(buyer["access_token"])
    ).json()["data"]
    return seller, buyer, trade


# ---------------------------------------------------------------------------
# 发送与持久化
# ---------------------------------------------------------------------------
def test_ws_send_message_persists(ws_client):
    """经 WS 发送的消息会落库，可通过 REST 会话详情读回。"""
    seller, buyer, trade = _trade_context(ws_client, "msg_s1", "msg_b1")
    conv_id = trade["conversation_id"]
    content = "你好，这本书还在吗？"

    with ws_client.websocket_connect(f"/ws?token={buyer['access_token']}") as ws:
        ws.send_json(
            {"event": "message:send", "conversation_id": conv_id, "content": content}
        )
        msg = ws.receive_json()
        assert msg["event"] == "message:new", msg
        assert msg["data"]["content"] == content

    detail = ws_client.get(
        f"/api/messages/conversations/{conv_id}", headers=auth_header(buyer["access_token"])
    )
    assert detail.status_code == 200, detail.text
    history = detail.json()["data"]
    assert history["total"] >= 1
    assert any(m["content"] == content for m in history["items"])


# 说明：「双方在线实时互收」的广播场景已由 tests/test_websocket.py
# ::test_ws_message_send_persists_and_broadcasts 覆盖并稳定通过，此处**不重复**
# ——双连接用例在退出 with 块时容易因子连接残留未读消息而挂死，
# 重复实现只会引入不稳定的测试。本文件聚焦"落库 + 业务约束"。


def test_ws_send_requires_conversation_id(ws_client):
    """缺少 conversation_id → 返回 42200 错误事件（不是断开连接）。"""
    buyer = register_login(ws_client, "msg_b3")
    with ws_client.websocket_connect(f"/ws?token={buyer['access_token']}") as ws:
        ws.send_json({"event": "message:send", "content": "没有会话号"})
        msg = ws.receive_json()
        assert msg["event"] == "error"
        assert msg["data"]["code"] == 42200


def test_ws_send_by_non_member_rejected(ws_client):
    """非会话成员发送消息 → 业务错误事件（越权防护）。"""
    seller, buyer, trade = _trade_context(ws_client, "msg_s4", "msg_b4")
    outsider = register_login(ws_client, "msg_out4")

    with ws_client.websocket_connect(f"/ws?token={outsider['access_token']}") as ws:
        ws.send_json(
            {
                "event": "message:send",
                "conversation_id": trade["conversation_id"],
                "content": "我不该能发这条",
            }
        )
        msg = ws.receive_json()
        assert msg["event"] == "error"
        assert msg["data"]["code"] != 0
    assert seller and buyer


def test_ws_invalid_json_returns_error(ws_client):
    """发送非 JSON → 42200 错误事件，连接保持。"""
    buyer = register_login(ws_client, "msg_b5")
    with ws_client.websocket_connect(f"/ws?token={buyer['access_token']}") as ws:
        ws.send_text("not-json-at-all")
        assert ws.receive_json()["data"]["code"] == 42200
        # 连接仍可用
        ws.send_json({"event": "ping"})
        assert ws.receive_json()["event"] == "pong"

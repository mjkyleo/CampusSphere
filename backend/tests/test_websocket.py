"""WebSocket 实时通信测试：鉴权、心跳、消息发送与广播、成员权限。"""

from __future__ import annotations

from helpers import auth_header, register_login


def _create_trade_context(client):
    """卖家发布物品 + 买家发起交易，返回 (seller, buyer, trade)。"""
    seller = register_login(client, "wsseller")
    buyer = register_login(client, "wsbuyer")
    r = client.post(
        "/api/items",
        json={
            "title": "WS 测试书本",
            "description": "九成新",
            "price": 1000,
            "category": "book",
            "images": [{"object_key": "misc/ws1.bin", "sort_order": 0}],
        },
        headers=auth_header(seller["access_token"]),
    )
    assert r.status_code == 200, r.text
    item = r.json()["data"]
    r2 = client.post(
        f"/api/items/{item['id']}/trade",
        headers=auth_header(buyer["access_token"]),
    )
    assert r2.status_code == 200, r2.text
    return seller, buyer, r2.json()["data"]


def test_ws_unauthorized_rejected(ws_client):
    """无 token（或无效 token）连接应收到 error 并断开。"""
    with ws_client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert msg["event"] == "error"
        assert msg["data"]["code"] == 40100


def test_ws_ping_pong(ws_client):
    """带合法 token 连接后，ping 应得到 pong。"""
    user = register_login(ws_client, "wsping")
    with ws_client.websocket_connect(f"/ws?token={user['access_token']}") as ws:
        ws.send_json({"event": "ping"})
        msg = ws.receive_json()
        assert msg["event"] == "pong"
        assert msg["data"] == {}


def test_ws_message_send_persists_and_broadcasts(ws_client):
    """买家发送消息：双方在线连接均收到 message:new，且消息落库。"""
    seller, buyer, trade = _create_trade_context(ws_client)
    conv_id = trade["conversation_id"]
    content = "你好，这本书还在吗？"

    with (
        ws_client.websocket_connect(f"/ws?token={buyer['access_token']}") as ws_buyer,
        ws_client.websocket_connect(f"/ws?token={seller['access_token']}") as ws_seller,
    ):
        ws_buyer.send_json(
            {"event": "message:send", "conversation_id": conv_id, "content": content}
        )
        evt_buyer = ws_buyer.receive_json()
        evt_seller = ws_seller.receive_json()

    assert evt_buyer["event"] == "message:new"
    assert evt_seller["event"] == "message:new"
    data = evt_buyer["data"]
    assert data["conversation_id"] == conv_id
    assert data["sender_id"] == buyer["user_id"]
    assert data["type"] == 0
    assert data["content"] == content
    assert evt_seller["data"]["content"] == content

    # 消息已持久化：通过 REST 历史接口校验
    r = ws_client.get(
        f"/api/messages/conversations/{conv_id}",
        headers=auth_header(buyer["access_token"]),
    )
    assert r.status_code == 200, r.text
    history = r.json()["data"]
    assert history["total"] == 1
    assert history["items"][0]["content"] == content


def test_ws_message_send_rejects_non_member(ws_client):
    """非会话成员发送消息应收到 error 事件，且不落库。"""
    seller, buyer, trade = _create_trade_context(ws_client)
    outsider = register_login(ws_client, "wsoutsider")
    conv_id = trade["conversation_id"]

    with ws_client.websocket_connect(f"/ws?token={outsider['access_token']}") as ws:
        ws.send_json(
            {"event": "message:send", "conversation_id": conv_id, "content": "闯入"}
        )
        msg = ws.receive_json()

    assert msg["event"] == "error"
    assert msg["data"]["code"] != 0

    # 数据库未被污染
    r = ws_client.get(
        f"/api/messages/conversations/{conv_id}",
        headers=auth_header(buyer["access_token"]),
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["total"] == 0

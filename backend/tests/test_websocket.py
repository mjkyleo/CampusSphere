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


# ---------------------------------------------------------------------------
# 断线补偿（Task 5）
# ---------------------------------------------------------------------------
def test_ws_reconnect_compensates_missed_messages_via_seq(ws_client):
    """断线重连：携带 last_seq 应**只**补发离线期间错过的消息。

    这条用例同时守护一个真实缺陷：重构前 ``_compensate`` 定义了却从未被
    调用，等于断线重连后什么都不补。
    """
    seller, buyer, trade = _create_trade_context(ws_client)
    conv_id = trade["conversation_id"]

    # 买家连发 3 条（卖家全程离线）—— 连接**串行**建立，不嵌套。
    # 每条发送后都要 draining 回包：TestClient 是单线程 portal，若发送侧
    # 不读回声，服务端 publish 回推会在 send_json 上积压并引发死锁，
    # 这与业务代码无关，是测试客户端的用法约定。
    with ws_client.websocket_connect(f"/ws?token={buyer['access_token']}") as ws:
        for content in ("第一条", "第二条", "第三条"):
            ws.send_json(
                {"event": "message:send", "conversation_id": conv_id, "content": content}
            )
            ws.receive_json()  # 丢弃自身回声，仅用于排空

    # 卖家带着 seq=2 重连：应**只**补发第 3 条
    with ws_client.websocket_connect(
        f"/ws?token={seller['access_token']}&conv={conv_id}&last_seq=2"
    ) as ws:
        compensated = ws.receive_json()

    assert compensated["event"] == "message:new", compensated
    assert compensated["data"]["content"] == "第三条"
    # 补发必须带 seq，客户端才能继续推进游标
    assert compensated["seq"] == 3


def test_ws_reconnect_with_up_to_date_seq_compensates_nothing(ws_client):
    """游标已是最新：不应补发任何消息（不能重复推已收到的那条）。"""
    seller, buyer, trade = _create_trade_context(ws_client)
    conv_id = trade["conversation_id"]

    # 卖家发 1 条（排空回声后断开），该消息拿到 seq=1
    with ws_client.websocket_connect(f"/ws?token={seller['access_token']}") as ws:
        ws.send_json(
            {"event": "message:send", "conversation_id": conv_id, "content": "唯一一条"}
        )
        ws.receive_json()

    # 用最新 seq 重连，随后发一条 ping 探活：若误补发，第一条收到的会是消息而非 pong
    with ws_client.websocket_connect(
        f"/ws?token={buyer['access_token']}&conv={conv_id}&last_seq=1"
    ) as ws:
        ws.send_json({"event": "ping"})
        got = ws.receive_json()

    assert got["event"] == "pong", f"不应补发已收到的消息，但收到了 {got}"


def test_ws_online_push_carries_seq(ws_client):
    """在线推送也必须带 seq：否则客户端无从推进游标，补发形同虚设。"""
    seller, buyer, trade = _create_trade_context(ws_client)
    conv_id = trade["conversation_id"]

    with (
        ws_client.websocket_connect(f"/ws?token={buyer['access_token']}") as ws_buyer,
        ws_client.websocket_connect(f"/ws?token={seller['access_token']}") as ws_seller,
    ):
        ws_seller.send_json(
            {"event": "message:send", "conversation_id": conv_id, "content": "带序号"}
        )
        # 发送方必须先排空自己的回声，否则服务端 publish 回推会阻塞（TestClient 单线程 portal 约定）
        ws_seller.receive_json()
        # buyer 收到的是同一条消息的在线推送，断言它带 seq
        got = ws_buyer.receive_json()

    assert got["event"] == "message:new", got
    assert got["seq"] == 1


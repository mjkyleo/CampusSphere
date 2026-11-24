"""WebSocket 实时通信测试：首帧鉴权、心跳、消息发送与广播、成员权限。

鉴权协议：连接建立后客户端须立即发送 ``{"event": "auth", "token": <jwt>}``，
服务端校验通过回 ``auth:ok``；token 不再走 URL 查询串（避免被反代访问日志记录）。
"""

from __future__ import annotations

from helpers import auth_header, key_from_token, open_ws, register_login


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
            "images": [{"object_key": key_from_token(seller["access_token"]), "sort_order": 0}],
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
    """首帧不是 auth（或 token 无效）应收到 error 并断开。"""
    with ws_client.websocket_connect("/ws") as ws:
        ws.send_json({"event": "ping"})  # 非鉴权帧抢占首帧位置
        msg = ws.receive_json()
        assert msg["event"] == "error"
        assert msg["data"]["code"] == 40100


def test_ws_invalid_token_rejected(ws_client):
    """auth 帧携带伪造 token 同样拒绝。"""
    with ws_client.websocket_connect("/ws") as ws:
        ws.send_json({"event": "auth", "token": "not.a.jwt"})
        msg = ws.receive_json()
        assert msg["event"] == "error"
        assert msg["data"]["code"] == 40100


def test_ws_ping_pong(ws_client):
    """鉴权通过后，ping 应得到 pong。"""
    user = register_login(ws_client, "wsping")
    with open_ws(ws_client, user["access_token"]) as ws:
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
        open_ws(ws_client, buyer["access_token"]) as ws_buyer,
        open_ws(ws_client, seller["access_token"]) as ws_seller,
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

    with open_ws(ws_client, outsider["access_token"]) as ws:
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
    with open_ws(ws_client, buyer["access_token"]) as ws:
        for content in ("第一条", "第二条", "第三条"):
            ws.send_json(
                {"event": "message:send", "conversation_id": conv_id, "content": content}
            )
            ws.receive_json()  # 丢弃自身回声，仅用于排空

    # 卖家带着 seq=2 重连：应**只**补发第 3 条
    with open_ws(ws_client, seller["access_token"], f"?conv={conv_id}&last_seq=2") as ws:
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
    with open_ws(ws_client, seller["access_token"]) as ws:
        ws.send_json(
            {"event": "message:send", "conversation_id": conv_id, "content": "唯一一条"}
        )
        ws.receive_json()

    # 用最新 seq 重连，随后发一条 ping 探活：若误补发，第一条收到的会是消息而非 pong
    with open_ws(ws_client, buyer["access_token"], f"?conv={conv_id}&last_seq=1") as ws:
        ws.send_json({"event": "ping"})
        got = ws.receive_json()

    assert got["event"] == "pong", f"不应补发已收到的消息，但收到了 {got}"


def test_ws_compensate_rejects_non_participant(ws_client):
    """非会话成员带 conv/last_seq 连接不得补发他人私聊历史（P0-2）。

    会话 ID 会经合法渠道泄露（如 TradeSessionOut.conversation_id 返回给买家），
    补发前必须校验连接者是会话参与者，否则任意登录用户都能拉取私聊内容。
    """
    seller, buyer, trade = _create_trade_context(ws_client)
    conv_id = trade["conversation_id"]

    # 买家先发 2 条离线消息进会话
    with open_ws(ws_client, buyer["access_token"]) as ws:
        for content in ("私信一", "私信二"):
            ws.send_json(
                {"event": "message:send", "conversation_id": conv_id, "content": content}
            )
            ws.receive_json()

    # 无关第三者拿到 conv_id 后试图按 seq 补发 → 应收到 40300 错误且收不到任何消息
    outsider = register_login(ws_client, "wsconvthief")
    with open_ws(ws_client, outsider["access_token"], f"?conv={conv_id}&last_seq=0") as ws:
        got = ws.receive_json()

    assert got["event"] == "error", f"非参与者不应收到补发消息，但收到了 {got}"
    assert got["data"]["code"] == 40300

    # 参与者不受影响：同样的请求由卖家发起应正常补发
    with open_ws(ws_client, seller["access_token"], f"?conv={conv_id}&last_seq=0") as ws:
        first = ws.receive_json()
    assert first["event"] == "message:new"
    assert first["data"]["content"] in ("私信一", "私信二")


def test_ws_online_push_carries_seq(ws_client):
    """在线推送也必须带 seq：否则客户端无从推进游标，补发形同虚设。"""
    seller, buyer, trade = _create_trade_context(ws_client)
    conv_id = trade["conversation_id"]

    with (
        open_ws(ws_client, buyer["access_token"]) as ws_buyer,
        open_ws(ws_client, seller["access_token"]) as ws_seller,
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

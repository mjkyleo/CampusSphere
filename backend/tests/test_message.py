"""消息测试：会话（由交易创建）、未读计数、已读回执。

发送消息通过 service 层直接落库（WebSocket 推送部分由集成环境覆盖）。
"""

from __future__ import annotations

from helpers import auth_header, register_login, run_async

from app.modules.message.models import Message


def test_conversation_unread_and_read(client, session_factory):
    seller = register_login(client, "msgseller")
    buyer = register_login(client, "msgbuyer")

    # 卖家发布物品，买家发起交易 -> 创建会话
    payload = {"title": "教材", "price": 100, "category": "book", "images": []}
    item = client.post(
        "/api/items", json=payload, headers=auth_header(seller["access_token"])
    ).json()["data"]
    trade = client.post(
        f"/api/items/{item['id']}/trade",
        headers=auth_header(buyer["access_token"]),
    ).json()["data"]
    conv_id = trade["conversation_id"]
    assert conv_id

    # 买家会话列表包含该会话
    r = client.get("/api/messages/conversations", headers=auth_header(buyer["access_token"]))
    assert r.status_code == 200
    convs = r.json()["data"]
    assert any(c["id"] == conv_id for c in convs)

    # 买家发一条消息（sender=buyer）
    async def _send():
        async with session_factory() as db:
            m = Message(
                conversation_id=conv_id,
                sender_id=buyer["user_id"],
                type=0,
                content="在吗",
                is_read=False,
            )
            db.add(m)
            await db.commit()

    run_async(_send())

    # 卖家未读应为 1，买家未读为 0
    su = client.get(
        "/api/messages/unread", headers=auth_header(seller["access_token"])
    ).json()["data"]["unread"]
    bu = client.get(
        "/api/messages/unread", headers=auth_header(buyer["access_token"])
    ).json()["data"]["unread"]
    assert su == 1
    assert bu == 0

    # 卖家标记已读
    r2 = client.post(
        f"/api/messages/conversations/{conv_id}/read",
        json={},
        headers=auth_header(seller["access_token"]),
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["marked"] == 1

    # 卖家未读归零
    su_after = client.get(
        "/api/messages/unread", headers=auth_header(seller["access_token"])
    ).json()["data"]["unread"]
    assert su_after == 0

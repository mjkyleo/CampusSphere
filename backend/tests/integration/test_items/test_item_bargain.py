"""议价会话（交易）集成测试：**创建会话 → 双方可见 → 越权隔离**。

二手交易的核心不是下单，而是"买家发起议价 → 自动生成私聊会话"。
这里覆盖会话的建立与访问边界；消息收发由
``integration/test_messaging/`` 覆盖（WebSocket 通道）。
"""

from __future__ import annotations

import pytest
from helpers import auth_header, register_login

pytestmark = pytest.mark.integration


def _publish(client, token: str, title: str = "议价测试物品") -> dict:
    r = client.post(
        "/api/items",
        json={
            "title": title,
            "description": "可议价",
            "price": 8000,
            "category": "书籍资料",
            "images": [{"object_key": "misc/deal.bin", "sort_order": 0}],
        },
        headers=auth_header(token),
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


# ---------------------------------------------------------------------------
# 正常流程
# ---------------------------------------------------------------------------
def test_buyer_starts_trade_creates_conversation(client):
    """买家发起交易 → 创建会话，返回 conversation_id。"""
    seller = register_login(client, "deal_seller")
    buyer = register_login(client, "deal_buyer")
    item = _publish(client, seller["access_token"])

    r = client.post(f"/api/items/{item['id']}/trade", headers=auth_header(buyer["access_token"]))
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["conversation_id"]
    assert data["item_id"] == item["id"]


def test_conversation_visible_to_both_parties(client):
    """买卖双方的会话列表中都能看到该会话。"""
    seller = register_login(client, "deal_s2")
    buyer = register_login(client, "deal_b2")
    item = _publish(client, seller["access_token"])
    conv_id = client.post(
        f"/api/items/{item['id']}/trade", headers=auth_header(buyer["access_token"])
    ).json()["data"]["conversation_id"]

    for tokens in (seller, buyer):
        r = client.get(
            "/api/messages/conversations", headers=auth_header(tokens["access_token"])
        )
        assert r.status_code == 200 and r.json()["code"] == 0, r.text
        ids = [c.get("id") or c.get("conversation_id") for c in r.json()["data"]]
        assert conv_id in ids, f"{tokens} 看不到会话: {r.text}"


def test_repeat_trade_is_rejected(client):
    """同一物品已有进行中的议价 → 再次发起被拒（并发加固后的期望行为）。

    早期实现是 check-then-act：先读 ``item.status`` 再插入会话，两步之间
    无锁。两个买家并发点"我想要"时都能读到 ON_SALE，于是同一物品出现多个
    活跃会话，继续往下走就是对同一件物品重复成交。

    现在改为**条件 UPDATE 原子抢占**（ON_SALE→RESERVED，受影响行数为 0 即
    判负），因此重复发起一定被 409 挡下，物品也只会保留一个活跃会话。
    """
    seller = register_login(client, "deal_s3")
    buyer = register_login(client, "deal_b3")
    item = _publish(client, seller["access_token"])

    first = client.post(
        f"/api/items/{item['id']}/trade", headers=auth_header(buyer["access_token"])
    )
    assert first.status_code == 200 and first.json()["code"] == 0, first.text

    second = client.post(
        f"/api/items/{item['id']}/trade", headers=auth_header(buyer["access_token"])
    )
    assert second.json()["code"] == 40900, second.text

    # 抢占成功后物品进入 RESERVED，广场上不该再显示"在售"
    detail = client.get(f"/api/items/{item['id']}").json()["data"]
    assert detail["status"] != 0, detail


def test_item_locked_after_trade_started(client):
    """抢占的原子性：物品被预订后，**其他买家**同样无法再发起议价。

    与上一条用例（同一买家重复点击）区分开：这里验证的是"一人抢到之后，
    所有后来者都被拒"，即 RESERVED 状态对全局生效，而非仅对发起者。
    """
    seller = register_login(client, "deal_s6")
    buyer1 = register_login(client, "deal_b6a")
    buyer2 = register_login(client, "deal_b6b")
    item = _publish(client, seller["access_token"])

    assert client.post(
        f"/api/items/{item['id']}/trade", headers=auth_header(buyer1["access_token"])
    ).json()["code"] == 0

    late = client.post(
        f"/api/items/{item['id']}/trade", headers=auth_header(buyer2["access_token"])
    )
    assert late.json()["code"] == 40900, late.text


def test_conversation_detail_readable_by_participant(client):
    """参与者可读取会话详情（消息列表）。"""
    seller = register_login(client, "deal_s4")
    buyer = register_login(client, "deal_b4")
    item = _publish(client, seller["access_token"])
    conv_id = client.post(
        f"/api/items/{item['id']}/trade", headers=auth_header(buyer["access_token"])
    ).json()["data"]["conversation_id"]

    r = client.get(
        f"/api/messages/conversations/{conv_id}", headers=auth_header(buyer["access_token"])
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text


# ---------------------------------------------------------------------------
# 边界与越权
# ---------------------------------------------------------------------------
def test_seller_cannot_trade_own_item(client):
    """卖家不能和自己议价。

    原为 xfail（``create_trade_session`` 未校验 buyer.id == item.owner_id），
    并发加固时顺手补上该校验，故移除 xfail 标记转为正式断言。
    """
    seller = register_login(client, "deal_self")
    item = _publish(client, seller["access_token"])

    r = client.post(
        f"/api/items/{item['id']}/trade", headers=auth_header(seller["access_token"])
    )
    assert r.json()["code"] != 0, "卖家与自己做成了交易（应被拒绝）"


def test_trade_requires_authentication(client):
    """未登录发起议价 → 401。"""
    seller = register_login(client, "deal_anon")
    item = _publish(client, seller["access_token"])

    r = client.post(f"/api/items/{item['id']}/trade")
    assert r.status_code == 401


def test_trade_on_nonexistent_item_returns_error(client):
    """对不存在的物品发起议价 → 业务错误（不是 500）。"""
    buyer = register_login(client, "deal_404")
    r = client.post(
        "/api/items/00000000-0000-0000-0000-000000000000/trade",
        headers=auth_header(buyer["access_token"]),
    )
    assert r.json()["code"] != 0


def test_outsider_cannot_read_conversation(client):
    """非参与者读取会话详情 → 拒绝（越权隔离 / IDOR 防护）。"""
    seller = register_login(client, "deal_s5")
    buyer = register_login(client, "deal_b5")
    outsider = register_login(client, "deal_out5")
    item = _publish(client, seller["access_token"])
    conv_id = client.post(
        f"/api/items/{item['id']}/trade", headers=auth_header(buyer["access_token"])
    ).json()["data"]["conversation_id"]

    r = client.get(
        f"/api/messages/conversations/{conv_id}",
        headers=auth_header(outsider["access_token"]),
    )
    assert r.json()["code"] != 0


def test_unread_endpoint_requires_auth(client):
    """未读数接口需登录。"""
    r = client.get("/api/messages/unread")
    assert r.status_code == 401

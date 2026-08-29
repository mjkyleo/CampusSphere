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


def test_repeat_trade_creates_new_session(client):
    """同一买家重复发起议价 → **每次新建一个会话**（当前实现无幂等复用）。

    这里固化现状：``create_trade_session`` 不做"买家+物品"唯一性校验，
    因此重复点击"我想要"会产生多条议价记录。若产品上希望复用会话，
    需在此处补充幂等逻辑并同步更新本用例。
    """
    seller = register_login(client, "deal_s3")
    buyer = register_login(client, "deal_b3")
    item = _publish(client, seller["access_token"])

    first = client.post(
        f"/api/items/{item['id']}/trade", headers=auth_header(buyer["access_token"])
    ).json()["data"]
    second = client.post(
        f"/api/items/{item['id']}/trade", headers=auth_header(buyer["access_token"])
    ).json()["data"]
    assert first["conversation_id"] != second["conversation_id"]
    assert first["item_id"] == second["item_id"] == item["id"]


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
@pytest.mark.xfail(
    reason="已知缺陷 P2：create_trade_session 未校验 buyer.id == item.owner_id，"
    "卖家可与自己议价并生成自会话（见 docs/TESTING.md 已知缺陷清单）",
    strict=False,
)
def test_seller_cannot_trade_own_item(client):
    """卖家不能和自己议价（**期望行为**，当前实现缺失该校验）。

    以 xfail 固化：一旦有人补上自交易校验，本用例会变为 XPASS 提醒更新标记；
    在此之前它不会阻塞 CI，但缺陷始终可见于测试报告。
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

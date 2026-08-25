"""二手物品测试：发布（多图）、列表、详情、状态机流转、发起交易会话。"""

from __future__ import annotations

from helpers import auth_header, register_login


def _create_item(client, token, title="二手自行车", price=19900):
    payload = {
        "title": title,
        "description": "九成新",
        "price": price,
        "category": "bike",
        "images": [{"object_key": "misc/abc123.bin", "sort_order": 0}],
    }
    r = client.post("/api/items", json=payload, headers=auth_header(token))
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_create_and_list_and_detail(client):
    user = register_login(client, "itemuser1")
    item = _create_item(client, user["access_token"])
    assert item["status"] == 0  # 上架
    assert item["id"]

    # 列表
    r = client.get("/api/items", headers=auth_header(user["access_token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    titles = [i["title"] for i in body["data"]["items"]]
    assert "二手自行车" in titles

    # 详情
    r2 = client.get(f"/api/items/{item['id']}", headers=auth_header(user["access_token"]))
    assert r2.status_code == 200
    assert r2.json()["data"]["id"] == item["id"]


def test_status_state_machine(client):
    user = register_login(client, "itemuser2")
    item = _create_item(client, user["access_token"])
    item_id = item["id"]
    h = auth_header(user["access_token"])

    # 上架 -> 下架
    r = client.patch(f"/api/items/{item_id}", json={"status": 1}, headers=h)
    assert r.status_code == 200
    assert r.json()["data"]["status"] == 1

    # 下架 -> 上架（合法回退）
    r = client.patch(f"/api/items/{item_id}", json={"status": 0}, headers=h)
    assert r.status_code == 200
    assert r.json()["data"]["status"] == 0

    # 上架 -> 已售（终态）
    r = client.patch(f"/api/items/{item_id}", json={"status": 2}, headers=h)
    assert r.status_code == 200
    assert r.json()["data"]["status"] == 2


def test_illegal_transition_rejected(client):
    user = register_login(client, "itemuser3")
    item = _create_item(client, user["access_token"])
    # 已售(2) 为终态，不可再流转到 上架(0)
    r = client.patch(f"/api/items/{item['id']}", json={"status": 2}, headers=auth_header(user["access_token"]))
    assert r.status_code == 200
    r2 = client.patch(f"/api/items/{item['id']}", json={"status": 0}, headers=auth_header(user["access_token"]))
    assert r2.status_code == 200
    assert r2.json()["code"] != 0  # 非法流转被拒


def test_trade_session_creates_conversation(client):
    seller = register_login(client, "itemseller")
    buyer = register_login(client, "itembuyer")
    item = _create_item(client, seller["access_token"])
    r = client.post(
        f"/api/items/{item['id']}/trade",
        headers=auth_header(buyer["access_token"]),
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["conversation_id"]
    assert data["buyer_id"] == buyer["user_id"]
    assert data["seller_id"] == seller["user_id"]

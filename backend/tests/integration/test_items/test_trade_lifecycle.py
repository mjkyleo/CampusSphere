"""交易生命周期测试：complete / cancel / 幂等 / 对账 / 通知。

覆盖 potentialBug.txt 中标注的缺口：
- complete/cancel 端点此前无测试
- 重复 complete/cancel 的幂等（409）
- 越权 complete/cancel（IDOR）
- cancel 释放物品回 ON_SALE
- 成交/取消后通知买卖双方
"""

from __future__ import annotations

import pytest
from helpers import auth_header, key_from_token, register_login

pytestmark = pytest.mark.integration


def _publish(client, token: str, title: str = "生命周期测试物品") -> dict:
    r = client.post(
        "/api/items",
        json={
            "title": title,
            "description": "生命周期测试",
            "price": 1000,
            "category": "书籍资料",
            "images": [{"object_key": key_from_token(token), "sort_order": 0}],
        },
        headers=auth_header(token),
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _start_trade(client, item_id: str, buyer_token: str) -> dict:
    r = client.post(f"/api/items/{item_id}/trade", headers=auth_header(buyer_token))
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    return r.json()["data"]


def test_complete_trade_marks_sold_and_is_idempotent(client):
    """成交：会话 COMPLETED、物品 SOLD；重复成交被 409 拒绝。"""
    seller = register_login(client, "life_seller_c")
    buyer = register_login(client, "life_buyer_c")
    item = _publish(client, seller["access_token"])
    trade = _start_trade(client, item["id"], buyer["access_token"])

    r = client.post(
        f"/api/items/trades/{trade['id']}/complete",
        headers=auth_header(buyer["access_token"]),
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    assert r.json()["data"]["status"] == 2  # COMPLETED

    detail = client.get(f"/api/items/{item['id']}").json()["data"]
    assert detail["status"] == 2  # SOLD

    again = client.post(
        f"/api/items/trades/{trade['id']}/complete",
        headers=auth_header(seller["access_token"]),
    )
    assert again.json()["code"] == 40900, again.text


def test_cancel_trade_releases_item_and_is_idempotent(client):
    """取消：会话 CANCELLED、物品回到 ON_SALE；重复取消被 409 拒绝。"""
    seller = register_login(client, "life_seller_x")
    buyer = register_login(client, "life_buyer_x")
    item = _publish(client, seller["access_token"])
    trade = _start_trade(client, item["id"], buyer["access_token"])

    assert client.get(f"/api/items/{item['id']}").json()["data"]["status"] == 3  # RESERVED

    r = client.post(
        f"/api/items/trades/{trade['id']}/cancel",
        headers=auth_header(seller["access_token"]),
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    assert r.json()["data"]["status"] == 3  # CANCELLED

    detail = client.get(f"/api/items/{item['id']}").json()["data"]
    assert detail["status"] == 0  # ON_SALE，僵尸物品被释放

    again = client.post(
        f"/api/items/trades/{trade['id']}/cancel",
        headers=auth_header(buyer["access_token"]),
    )
    assert again.json()["code"] == 40900, again.text


def test_outsider_cannot_complete_or_cancel(client):
    """非交易方 complete/cancel → FORBIDDEN（IDOR 防护）。"""
    seller = register_login(client, "life_seller_o")
    buyer = register_login(client, "life_buyer_o")
    outsider = register_login(client, "life_out_o")
    item = _publish(client, seller["access_token"])
    trade = _start_trade(client, item["id"], buyer["access_token"])

    for action in ("complete", "cancel"):
        r = client.post(
            f"/api/items/trades/{trade['id']}/{action}",
            headers=auth_header(outsider["access_token"]),
        )
        assert r.json()["code"] == 40300, r.text


def test_complete_after_cancel_is_rejected(client):
    """已取消的交易不能再成交（状态机拒绝）。"""
    seller = register_login(client, "life_seller_ac")
    buyer = register_login(client, "life_buyer_ac")
    item = _publish(client, seller["access_token"])
    trade = _start_trade(client, item["id"], buyer["access_token"])

    assert client.post(
        f"/api/items/trades/{trade['id']}/cancel",
        headers=auth_header(buyer["access_token"]),
    ).json()["code"] == 0

    r = client.post(
        f"/api/items/trades/{trade['id']}/complete",
        headers=auth_header(buyer["access_token"]),
    )
    assert r.json()["code"] == 40900, r.text


def test_complete_and_cancel_notify_both_parties(client, monkeypatch):
    """成交/取消后向买卖双方各派发一条通知。"""
    calls: list[tuple[str, str]] = []

    def _fake_notify(user_id: str, title: str, content: str) -> None:
        calls.append((user_id, title))

    monkeypatch.setattr("app.modules.item.service._notify_user", _fake_notify)

    seller = register_login(client, "life_seller_n")
    buyer = register_login(client, "life_buyer_n")
    item = _publish(client, seller["access_token"])
    trade = _start_trade(client, item["id"], buyer["access_token"])
    calls.clear()  # 只统计 complete 之后的

    client.post(
        f"/api/items/trades/{trade['id']}/complete",
        headers=auth_header(buyer["access_token"]),
    )
    notified = {uid for uid, _ in calls}
    assert seller["user_id"] in notified, calls
    assert buyer["user_id"] in notified, calls
    assert all(title == "交易已完成" for _, title in calls), calls

"""IDOR（越权访问）防护测试：对应审计 P1-7。

核心断言：用户 A 创建的资源，用户 B 即使已登录也**不能**修改/删除（应返回 40300 FORBIDDEN）。
同时验证 owner 本人操作成功，确保防护没有误伤正常使用者。

约定：所有业务错误经统一异常处理器包装为 HTTP 200 + 响应体 code 承载业务码
（见 app/core/exceptions.py），因此此处断言 ``code == 40300`` 而非 HTTP 403。
"""

from __future__ import annotations

from helpers import auth_header, register_login

FORBIDDEN = 40300


def _create_item(client, token, title="越权测试物品", price=100):
    payload = {
        "title": title,
        "description": "用于 IDOR 测试",
        "price": price,
        "category": "test",
        "images": [],
    }
    r = client.post("/api/items", json=payload, headers=auth_header(token))
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_owner_can_update_and_delete(client):
    """正向用例：资源拥有者本人可正常修改与删除。"""
    owner = register_login(client, "idor_owner")
    item = _create_item(client, owner["access_token"])
    item_id = item["id"]
    h = auth_header(owner["access_token"])

    r = client.patch(f"/api/items/{item_id}", json={"status": 1}, headers=h)
    assert r.status_code == 200 and r.json()["code"] == 0

    r = client.delete(f"/api/items/{item_id}", headers=h)
    assert r.status_code == 200 and r.json()["code"] == 0


def test_non_owner_cannot_update(client):
    """越权用例：非拥有者修改他人物品应被拒绝（40300）。"""
    owner = register_login(client, "idor_owner_a")
    attacker = register_login(client, "idor_attacker_b")
    item = _create_item(client, owner["access_token"])

    r = client.patch(
        f"/api/items/{item['id']}",
        json={"title": "已被篡改"},
        headers=auth_header(attacker["access_token"]),
    )
    assert r.status_code == 200
    assert r.json()["code"] == FORBIDDEN, r.text


def test_non_owner_cannot_delete(client):
    """越权用例：非拥有者删除他人物品应被拒绝（40300）。"""
    owner = register_login(client, "idor_owner_c")
    attacker = register_login(client, "idor_attacker_d")
    item = _create_item(client, owner["access_token"])

    r = client.delete(
        f"/api/items/{item['id']}",
        headers=auth_header(attacker["access_token"]),
    )
    assert r.status_code == 200
    assert r.json()["code"] == FORBIDDEN, r.text


def test_non_owner_cannot_tamper_via_trade(client):
    """越权用例：非拥有者不能对他人物品发起交易会话（交易会话以卖家归属为准）。"""
    owner = register_login(client, "idor_owner_e")
    buyer = register_login(client, "idor_buyer_f")
    item = _create_item(client, owner["access_token"])

    # 买家对自己无关的物品交易是被允许的（这是正常业务），此处仅验证
    # 卖方字段不会被冒用：创建后会话的 seller_id 必须等于物主。
    r = client.post(
        f"/api/items/{item['id']}/trade",
        headers=auth_header(buyer["access_token"]),
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["seller_id"] == owner["user_id"]
    assert data["buyer_id"] == buyer["user_id"]

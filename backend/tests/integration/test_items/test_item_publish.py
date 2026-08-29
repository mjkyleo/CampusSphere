"""二手物品发布集成测试：**填表 → 提交 → 列表可见 → 详情 → 下架 → 删除**。

对应核心用户旅程中的"发布二手"。默认配置下 ``items.review.enabled=false``
（见 ``config/school.yaml``），即**发布即上架**；若后台开启审核，
新物品会进入 PENDING 而不出现在在售列表中，此差异由
``test_publish_with_review_enabled`` 单独覆盖。
"""

from __future__ import annotations

import uuid

import pytest  # type: ignore[reportMissingImports]

from app.common.enums import ItemStatus
from factories import ItemFactory
from helpers import auth_header, register_login

pytestmark = pytest.mark.integration


def _publish(client, token: str, **overrides):
    """发布一件二手物品。"""
    payload = {
        "title": overrides.get("title", f"闲置自行车_{uuid.uuid4().hex[:6]}"),
        "description": overrides.get("description", "九成新，校内面交"),
        "price": overrides.get("price", 12000),
        "category": overrides.get("category", "电子产品"),
        "images": overrides.get("images", [{"object_key": "misc/bike.bin", "sort_order": 0}]),
    }
    return client.post("/api/items", json=payload, headers=auth_header(token))


# ---------------------------------------------------------------------------
# 正常流程
# ---------------------------------------------------------------------------
def test_publish_item_returns_item(client):
    """发布成功：返回物品完整字段，默认在售。"""
    tokens = register_login(client, "pub_seller")
    r = _publish(client, tokens["access_token"])
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["id"]
    assert data["status"] == ItemStatus.ON_SALE.value
    assert data["price"] == 12000
    assert len(data["images"]) == 1


def test_published_item_appears_in_list(client):
    """发布后可在公开列表中查到（旅程：列表可见）。"""
    tokens = register_login(client, "pub_list_seller")
    item = _publish(client, tokens["access_token"]).json()["data"]

    lst = client.get("/api/items")
    assert lst.status_code == 200 and lst.json()["code"] == 0
    ids = [i["id"] for i in lst.json()["data"]["items"]]
    assert item["id"] in ids


def test_published_item_detail_is_readable_without_login(client):
    """详情页未登录也可浏览（需求：未登录可浏览，仅写操作需登录）。"""
    tokens = register_login(client, "pub_detail_seller")
    item = _publish(client, tokens["access_token"]).json()["data"]

    r = client.get(f"/api/items/{item['id']}")
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    assert r.json()["data"]["title"] == item["title"]


def test_owner_can_off_shelf(client):
    """下架后不再出现在"在售"列表中。"""
    tokens = register_login(client, "pub_off_seller")
    item = _publish(client, tokens["access_token"]).json()["data"]

    patch = client.patch(
        f"/api/items/{item['id']}",
        json={"status": ItemStatus.OFF_SHELF.value},
        headers=auth_header(tokens["access_token"]),
    )
    assert patch.status_code == 200 and patch.json()["code"] == 0, patch.text

    on_sale = client.get("/api/items", params={"status": ItemStatus.ON_SALE.value})
    assert item["id"] not in [i["id"] for i in on_sale.json()["data"]["items"]]


def test_owner_can_delete_item(client):
    """删除后详情不可访问。"""
    tokens = register_login(client, "pub_del_seller")
    item = _publish(client, tokens["access_token"]).json()["data"]

    dele = client.delete(
        f"/api/items/{item['id']}", headers=auth_header(tokens["access_token"])
    )
    assert dele.status_code == 200 and dele.json()["code"] == 0, dele.text

    detail = client.get(f"/api/items/{item['id']}")
    assert detail.json()["code"] != 0


# ---------------------------------------------------------------------------
# 筛选与搜索
# ---------------------------------------------------------------------------
def test_list_filter_by_category(client):
    """按分类筛选：只返回该分类物品。"""
    tokens = register_login(client, "pub_cat_seller")
    _publish(client, tokens["access_token"], category="书籍资料", title="数据结构教材")
    other = _publish(
        client, tokens["access_token"], category="交通工具", title="折叠伞"
    ).json()["data"]

    r = client.get("/api/items", params={"category": "书籍资料"})
    assert r.status_code == 200
    ids = [i["id"] for i in r.json()["data"]["items"]]
    assert other["id"] not in ids


def test_list_filter_by_keyword(client):
    """按关键词模糊搜索标题。"""
    tokens = register_login(client, "pub_kw_seller")
    marker = f"稀有关键词{uuid.uuid4().hex[:6]}"
    item = _publish(client, tokens["access_token"], title=f"{marker} 台灯").json()["data"]

    r = client.get("/api/items", params={"keyword": marker})
    assert r.status_code == 200
    assert item["id"] in [i["id"] for i in r.json()["data"]["items"]]


def test_list_pagination(client):
    """分页参数生效：page_size 限制返回条数。"""
    tokens = register_login(client, "pub_page_seller")
    for _ in range(3):
        _publish(client, tokens["access_token"])

    r = client.get("/api/items", params={"page": 1, "page_size": 2})
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data["items"]) <= 2
    assert data["page_size"] == 2


# ---------------------------------------------------------------------------
# 权限与校验
# ---------------------------------------------------------------------------
def test_publish_requires_authentication(client):
    """未登录发布 → 网关 401（需求：未登录的写操作重定向/拒绝）。"""
    r = client.post("/api/items", json={"title": "未登录发布的物品"})
    assert r.status_code == 401


def test_publish_rejects_empty_title(client):
    """标题为空 → 校验失败（schema min_length=1）。"""
    tokens = register_login(client, "pub_bad_seller")
    r = client.post("/api/items", json={"title": ""}, headers=auth_header(tokens["access_token"]))
    assert r.status_code == 422


def test_publish_rejects_negative_price(client):
    """价格为负 → 校验失败（schema ge=0）。"""
    tokens = register_login(client, "pub_neg_seller")
    r = client.post(
        "/api/items", json={"title": "负价物品", "price": -1}, headers=auth_header(tokens["access_token"])
    )
    assert r.status_code == 422


def test_non_owner_cannot_off_shelf(client):
    """越权下架他人物品 → 拒绝（IDOR 防护）。"""
    owner = register_login(client, "pub_owner_x")
    other = register_login(client, "pub_other_x")
    item = _publish(client, owner["access_token"]).json()["data"]

    r = client.patch(
        f"/api/items/{item['id']}",
        json={"status": ItemStatus.OFF_SHELF.value},
        headers=auth_header(other["access_token"]),
    )
    assert r.json()["code"] != 0


# ---------------------------------------------------------------------------
# 工厂播种：验证工厂与 API 契约一致
# ---------------------------------------------------------------------------
async def test_factory_seeded_items_are_queryable(client, fx):
    """用 factory_boy 直接播种的物品可被列表接口查到。

    这条用例同时是**数据工厂的健康检查**：若模型字段与工厂定义漂移
    （例如新增了非空列而工厂未提供默认值），这里会第一个失败。
    """
    owner = await fx.create(ItemFactory)  # owner_id 为随机 UUID，仅用于列表可见性
    lst = client.get("/api/items")
    assert lst.status_code == 200
    assert owner.id in [i["id"] for i in lst.json()["data"]["items"]]

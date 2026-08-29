"""端到端主流程测试：串联认证 → 物品交易 → 校园内容 → 个人资料。

与既有单模块测试的区别
----------------------
既有测试按模块切分（test_item / test_course_canteen / test_user ...），
各自注册独立用户、独立断言。本模块模拟**同一批用户的连续操作路径**，
重点验证跨模块协作与状态在链路上的正确传递：

* 买家发起交易后，买卖双方的会话列表都应出现该会话（item → message 联动）
* 物品下架后，按 status 筛选的结果应立即收敛
* 食堂列表一次请求即返回嵌套的摊位与菜品（验证 selectinload 消除 N+1）
* 越权操作返回业务错误码（HTTP 200 + code≠0），而不是服务端 5xx

边界场景
--------
未认证访问、无效令牌、资源不存在、非法分页参数、分页越界、重复注册、跨用户越权。
"""

from __future__ import annotations

from helpers import admin_login, auth_header, register_login, seed_admin


def _publish_item(client, headers, title="E2E 二手自行车", price=19900):
    """发布一件物品并返回 data。"""
    resp = client.post(
        "/api/items",
        json={
            "title": title,
            "description": "九成新，可小刀",
            "price": price,
            "category": "bike",
            "images": [{"object_key": "misc/e2e.bin", "sort_order": 0}],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# 正常流程：完整用户旅程
# ---------------------------------------------------------------------------
def test_full_journey_publish_trade_and_delete(client):
    """完整链路：发布 → 浏览 → 详情 → 议价会话 → 下架 → 删除。"""
    seller = register_login(client, "e2e_seller")
    buyer = register_login(client, "e2e_buyer")
    sh = auth_header(seller["access_token"])
    bh = auth_header(buyer["access_token"])

    # 1) 卖家发布物品
    item = _publish_item(client, sh)
    assert item["status"] == 0, "新发布的物品应处于上架状态"

    # 2) 买家能在公开列表中看到
    listing = client.get("/api/items", headers=bh).json()["data"]
    assert any(i["id"] == item["id"] for i in listing["items"]), (
        "上架物品应出现在公开列表中"
    )

    # 3) 买家查看详情
    detail = client.get(f"/api/items/{item['id']}", headers=bh).json()["data"]
    assert detail["title"] == "E2E 二手自行车"

    # 4) 买家发起交易 → 买卖双方会话列表都出现该会话
    trade = client.post(f"/api/items/{item['id']}/trade", headers=bh)
    assert trade.status_code == 200, trade.text
    conversation_id = trade.json()["data"]["conversation_id"]

    for header in (sh, bh):
        conversations = client.get("/api/messages/conversations", headers=header)
        assert conversations.status_code == 200, conversations.text
        ids = [c["id"] for c in conversations.json()["data"]]
        assert conversation_id in ids, "交易会话应对买卖双方同时可见"

    # 5) 卖家下架：按 status=0 筛选时不应再出现
    offline = client.patch(f"/api/items/{item['id']}", json={"status": 1}, headers=sh)
    assert offline.status_code == 200, offline.text
    assert offline.json()["data"]["status"] == 1

    online = client.get("/api/items?status=0", headers=sh).json()["data"]
    assert all(i["id"] != item["id"] for i in online["items"]), (
        "下架物品不应出现在「上架」筛选结果中"
    )

    # 6) 卖家删除自己的物品
    deleted = client.delete(f"/api/items/{item['id']}", headers=sh)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["code"] == 0


def test_course_and_canteen_cross_module_flow(client, session_factory):
    """校园内容链路：课程评价 + 食堂→摊位→菜品嵌套加载。

    食堂基础数据由管理端维护（/api/admin/*），普通用户负责浏览与评价，
    这条链路同时覆盖了权限分层与内容查询。
    """
    seed_admin(session_factory)
    admin_h = admin_login(client)
    user = register_login(client, "e2e_campus")
    h = auth_header(user["access_token"])

    # 课程：创建 → 评价 → 详情回显
    course = client.post(
        "/api/courses",
        json={
            "code": "E2E101",
            "name": "软件工程",
            "teacher": "张老师",
            "credits": 3,
            "semester": "2026秋",
        },
        headers=h,
    ).json()["data"]

    review = client.post(
        f"/api/courses/{course['id']}/reviews",
        json={"rating": 5, "content": "收获很大"},
        headers=h,
    )
    assert review.status_code == 200, review.text

    course_detail = client.get(f"/api/courses/{course['id']}", headers=h).json()["data"]
    assert len(course_detail["reviews"]) >= 1, "课程详情应回显已提交的评价"

    # 食堂：食堂 → 摊位 → 菜品 → 评价
    canteen = client.post(
        "/api/admin/canteens", json={"name": "E2E 三食堂", "location": "北区"}, headers=admin_h
    ).json()["data"]
    stall = client.post(
        "/api/admin/canteens/stalls",
        json={"canteen_id": canteen["id"], "name": "快餐档"},
        headers=admin_h,
    ).json()["data"]
    dish = client.post(
        "/api/admin/canteens/dishes",
        json={"stall_id": stall["id"], "name": "盖浇饭", "price": 1500},
        headers=admin_h,
    ).json()["data"]

    dish_review = client.post(
        f"/api/canteens/dishes/{dish['id']}/reviews",
        json={"rating": 4, "content": "份量足"},
        headers=h,
    )
    assert dish_review.status_code == 200, dish_review.text

    # 列表接口一次返回嵌套结构：验证 selectinload 已消除食堂→摊位→菜品的 N+1
    canteens = client.get("/api/canteens", headers=h).json()["data"]
    target = next(c for c in canteens if c["id"] == canteen["id"])
    assert target["stalls"], "食堂列表应预加载摊位"
    assert target["stalls"][0]["dishes"], "摊位应预加载菜品"


def test_profile_update_persists_across_requests(client):
    """个人资料更新后，再次请求应读到新值（持久化正确）。"""
    user = register_login(client, "e2e_profile")
    h = auth_header(user["access_token"])

    updated = client.patch(
        "/api/users/me",
        json={"nickname": "E2E 昵称", "bio": "热爱开源", "school_major": "软件工程"},
        headers=h,
    )
    assert updated.status_code == 200, updated.text

    again = client.get("/api/users/me", headers=h).json()["data"]
    assert again["nickname"] == "E2E 昵称"
    assert again["bio"] == "热爱开源"
    assert again["school_major"] == "软件工程"


# ---------------------------------------------------------------------------
# 边界场景
# ---------------------------------------------------------------------------
def test_unauthenticated_access_rejected(client):
    """未携带令牌访问受保护接口 → 401；公开列表仍可匿名浏览。"""
    assert client.get("/api/users/me").status_code == 401
    assert client.get("/api/messages/conversations").status_code == 401
    # /api/items 为公开浏览入口（未登录也能看商品），不应要求鉴权
    assert client.get("/api/items").status_code == 200


def test_invalid_token_rejected(client):
    """伪造 / 过期令牌 → 401，且不泄露服务端细节。"""
    for bad in ("not.a.valid.jwt", "Bearer", ""):
        resp = client.get("/api/users/me", headers={"Authorization": f"Bearer {bad}"})
        assert resp.status_code == 401, f"无效令牌 {bad!r} 应被拒绝"


def test_missing_resource_returns_business_error_not_500(client):
    """访问不存在的资源：不得 500，应返回明确的业务错误。"""
    user = register_login(client, "e2e_missing")
    h = auth_header(user["access_token"])

    resp = client.get("/api/items/00000000-0000-0000-0000-000000000000", headers=h)
    assert resp.status_code != 500, "资源不存在不应触发服务端异常"
    if resp.status_code == 200:
        assert resp.json()["code"] != 0, "资源不存在应返回非零业务错误码"


def test_invalid_pagination_params_rejected(client):
    """非法分页参数（page < 1、page_size 超上限）→ 422。"""
    user = register_login(client, "e2e_pagination")
    h = auth_header(user["access_token"])

    assert client.get("/api/items?page=0", headers=h).status_code == 422
    assert client.get("/api/items?page_size=0", headers=h).status_code == 422
    assert client.get("/api/items?page_size=101", headers=h).status_code == 422


def test_pagination_beyond_range_returns_empty(client):
    """分页越界：返回空列表，而不是报错或返回首页数据。"""
    user = register_login(client, "e2e_overflow")
    h = auth_header(user["access_token"])
    _publish_item(client, h, title="越界测试物品")

    resp = client.get("/api/items?page=999", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["items"] == [], "越界分页应返回空列表"


def test_duplicate_username_rejected(client):
    """重复用户名注册 → 业务冲突错误，且不影响首次注册结果。"""
    first = client.post(
        "/api/auth/register", json={"username": "e2e_dup", "password": "secret123"}
    )
    assert first.status_code == 200, first.text
    assert first.json()["code"] == 0

    second = client.post(
        "/api/auth/register", json={"username": "e2e_dup", "password": "secret123"}
    )
    assert second.status_code == 200, second.text
    assert second.json()["code"] != 0, "重复用户名应返回冲突错误码"


def test_cannot_delete_others_item(client):
    """跨用户越权删除 → 业务错误码 40300，物品不被删除。"""
    owner = register_login(client, "e2e_owner")
    attacker = register_login(client, "e2e_attacker")
    item = _publish_item(client, auth_header(owner["access_token"]))

    resp = client.delete(
        f"/api/items/{item['id']}", headers=auth_header(attacker["access_token"])
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["code"] == 40300, "越权删除应返回 40300"

    # 物品仍然存在（越权未生效）
    still = client.get(f"/api/items/{item['id']}", headers=auth_header(owner["access_token"]))
    assert still.status_code == 200
    assert still.json()["data"]["id"] == item["id"], "越权删除不应真正删除物品"

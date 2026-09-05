"""食堂评价集成测试：**选食堂 → 看档口 → 选菜品 → 打分**。

食堂/档口/菜品是三级嵌套结构（Canteen → Stall → Dish），
用 ``factory_boy`` 逐级播种，外键由测试显式指定，保证数据真实可 Join。
"""

from __future__ import annotations

import pytest
from factories import CanteenFactory, CanteenReviewFactory, DishFactory, StallFactory
from helpers import auth_header, register_login

pytestmark = pytest.mark.integration


async def _seed_chain(fx):
    """播种 食堂 → 档口 → 菜品，返回三者的最小字段集。"""
    canteen = await fx.create(CanteenFactory)
    stall = await fx.create(StallFactory, canteen_id=canteen.id)
    dish = await fx.create(DishFactory, stall_id=stall.id)
    return canteen, stall, dish


# ---------------------------------------------------------------------------
# 浏览链路（无需登录）
# ---------------------------------------------------------------------------
async def test_canteen_list_includes_seeded_canteen(client, fx):
    """食堂列表可浏览（未登录也应可见）。"""
    canteen, _, _ = await _seed_chain(fx)
    r = client.get("/api/canteens")
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    assert canteen.id in [c["id"] for c in r.json()["data"]]


async def test_canteen_detail_includes_stalls(client, fx):
    """食堂详情含档口列表（旅程：查看档口）。"""
    canteen, stall, _ = await _seed_chain(fx)
    r = client.get(f"/api/canteens/{canteen.id}")
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["id"] == canteen.id
    assert stall.id in [s["id"] for s in data.get("stalls", [])]


async def test_dish_detail_is_readable(client, fx):
    """菜品详情可查看。"""
    _, _, dish = await _seed_chain(fx)
    r = client.get(f"/api/canteens/dishes/{dish.id}")
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    # 详情为 {"dish": {...}, "reviews": [...]} 的嵌套结构
    assert r.json()["data"]["dish"]["id"] == dish.id


# ---------------------------------------------------------------------------
# 打分
# ---------------------------------------------------------------------------
async def test_rate_dish_success(client, fx):
    """登录用户对菜品打分（旅程：对菜品评分）。"""
    _, _, dish = await _seed_chain(fx)
    tokens = register_login(client, "dish_rater")

    r = client.post(
        f"/api/canteens/dishes/{dish.id}/reviews",
        json={"rating": 4, "content": "分量足，味道不错"},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    created = r.json()["data"]
    assert created["rating"] == 4
    assert created["dish_id"] == dish.id


async def test_rate_dish_requires_auth(client, fx):
    """未登录打分 → 401。"""
    _, _, dish = await _seed_chain(fx)
    r = client.post(
        f"/api/canteens/dishes/{dish.id}/reviews", json={"rating": 5, "content": "匿名"}
    )
    assert r.status_code == 401


@pytest.mark.parametrize("bad_rating", [0, 6])
async def test_rate_dish_rejects_out_of_range(client, fx, bad_rating):
    """评分越界 → 422。"""
    _, _, dish = await _seed_chain(fx)
    tokens = register_login(client, f"dish_bad_{bad_rating}")
    r = client.post(
        f"/api/canteens/dishes/{dish.id}/reviews",
        json={"rating": bad_rating},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.status_code == 422


async def test_dish_reviews_are_isolated(client, fx):
    """不同菜品的评价互不串扰。"""
    c1, s1, d1 = await _seed_chain(fx)
    _, _, d2 = await _seed_chain(fx)
    await fx.create(CanteenReviewFactory, dish_id=d1.id, content="菜品一评价")
    await fx.create(CanteenReviewFactory, dish_id=d2.id, content="菜品二评价")

    detail = client.get(f"/api/canteens/dishes/{d1.id}").json()["data"]
    contents = [rv.get("content") for rv in detail.get("reviews", [])]
    assert "菜品一评价" in contents
    assert "菜品二评价" not in contents
    assert c1.id and s1.id

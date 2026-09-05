"""课程评价集成测试：**搜索课程 → 查看详情 → 发表评价 → 列表回显**。

课程数据由 ``factory_boy`` 播种（CourseFactory），避免每个用例都走一遍
"建课程"的写接口，从而把断言聚焦在**评价链路**本身。
"""

from __future__ import annotations

import uuid

import pytest
from factories import CourseFactory, CourseReviewFactory
from helpers import auth_header, register_login

pytestmark = pytest.mark.integration


async def _seed_course(fx, **overrides) -> dict:
    """播种一门课程并返回可断言的最小字段集。"""
    course = await fx.create(CourseFactory, **overrides)
    return {"id": course.id, "name": course.name, "code": course.code}


# ---------------------------------------------------------------------------
# 搜索与详情
# ---------------------------------------------------------------------------
async def test_search_course_by_keyword(client, fx):
    """按关键词搜索课程（旅程：搜索课程）。"""
    marker = f"量子烘焙学{uuid.uuid4().hex[:4]}"
    course = await _seed_course(fx, name=marker)

    r = client.get("/api/courses", params={"keyword": marker})
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    items = r.json()["data"]["items"]
    assert course["id"] in [c["id"] for c in items]


async def test_search_course_by_department(client, fx):
    """按开课院系筛选。"""
    dept = f"稀有院系{uuid.uuid4().hex[:4]}"
    course = await _seed_course(fx, department=dept)
    other = await _seed_course(fx, department="计算机学院")

    r = client.get("/api/courses", params={"department": dept})
    assert r.status_code == 200
    ids = [c["id"] for c in r.json()["data"]["items"]]
    assert course["id"] in ids
    assert other["id"] not in ids


async def test_course_detail_returns_course_and_reviews(client, fx):
    """详情页返回课程本体 + 评价列表。"""
    course = await _seed_course(fx)
    review = await fx.create(
        CourseReviewFactory, course_id=course["id"], rating=4, content="老师讲得清楚"
    )

    r = client.get(f"/api/courses/{course['id']}")
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    data = r.json()["data"]
    assert data["course"]["id"] == course["id"]
    assert any(rv["id"] == review.id for rv in data["reviews"])


async def test_course_detail_not_found(client):
    """不存在的课程 → 业务错误（不是 500）。"""
    r = client.get("/api/courses/00000000-0000-0000-0000-000000000000")
    assert r.json()["code"] != 0


# ---------------------------------------------------------------------------
# 发表评价
# ---------------------------------------------------------------------------
async def test_add_review_success(client, fx):
    """登录用户发表评价 → 详情页可见（旅程：发表评价）。"""
    course = await _seed_course(fx)
    tokens = register_login(client, "course_reviewer")

    r = client.post(
        f"/api/courses/{course['id']}/reviews",
        json={"rating": 5, "content": "收获很大，推荐选修"},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    created = r.json()["data"]
    assert created["rating"] == 5
    assert created["content"] == "收获很大，推荐选修"

    detail = client.get(f"/api/courses/{course['id']}")
    assert any(rv["id"] == created["id"] for rv in detail.json()["data"]["reviews"])


async def test_add_review_requires_auth(client, fx):
    """未登录发表评价 → 401（未登录可浏览，写操作需登录）。"""
    course = await _seed_course(fx)
    r = client.post(
        f"/api/courses/{course['id']}/reviews", json={"rating": 5, "content": "匿名评价"}
    )
    assert r.status_code == 401


@pytest.mark.parametrize("bad_rating", [0, 6, -1])
async def test_add_review_rejects_out_of_range_rating(client, fx, bad_rating):
    """评分越界（1-5 之外）→ 422。"""
    course = await _seed_course(fx)
    tokens = register_login(client, f"course_rater_{abs(bad_rating)}")

    r = client.post(
        f"/api/courses/{course['id']}/reviews",
        json={"rating": bad_rating, "content": "越界评分"},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.status_code == 422


async def test_add_review_to_missing_course(client):
    """对不存在的课程评价 → 业务错误。"""
    tokens = register_login(client, "course_missing")
    r = client.post(
        "/api/courses/00000000-0000-0000-0000-000000000000/reviews",
        json={"rating": 5},
        headers=auth_header(tokens["access_token"]),
    )
    assert r.json()["code"] != 0


async def test_reviews_are_isolated_between_courses(client, fx):
    """不同课程的评价互不串扰。"""
    c1 = await _seed_course(fx)
    c2 = await _seed_course(fx)
    r1 = await fx.create(CourseReviewFactory, course_id=c1["id"], content="课程一评价")
    await fx.create(CourseReviewFactory, course_id=c2["id"], content="课程二评价")

    detail = client.get(f"/api/courses/{c1['id']}").json()["data"]
    contents = [rv["content"] for rv in detail["reviews"]]
    assert "课程一评价" in contents
    assert "课程二评价" not in contents
    assert r1.id

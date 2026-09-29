"""课程 / 食堂测试：课程评价、食堂-摊位-菜品-评价链路。"""

from __future__ import annotations

import pytest
from helpers import admin_login, auth_header, register_login, seed_admin, run_async


def test_course_create_and_review(client):
    user = register_login(client, "courseuser1")
    h = auth_header(user["access_token"])

    c = client.post(
        "/api/courses",
        json={"code": "CS101", "name": "数据结构", "teacher": "李老师", "credits": 3, "semester": "2025秋"},
        headers=h,
    )
    assert c.status_code == 200, c.text
    course_id = c.json()["data"]["id"]

    rev = client.post(
        f"/api/courses/{course_id}/reviews",
        json={"rating": 5, "content": "老师讲得很好"},
        headers=h,
    )
    assert rev.status_code == 200
    assert rev.json()["data"]["rating"] == 5

    detail = client.get(f"/api/courses/{course_id}", headers=h)
    assert detail.status_code == 200
    assert len(detail.json()["data"]["reviews"]) >= 1


def test_course_review_duplicate_rejected(client):
    """同一用户重复评价同一课程 → 409（P1-7：应用层 + 唯一索引双保险）。"""
    user = register_login(client, "coursedup1")
    h = auth_header(user["access_token"])
    c = client.post(
        "/api/courses",
        json={"code": "CS201", "name": "操作系统", "teacher": "张", "credits": 3, "semester": "2025秋"},
        headers=h,
    ).json()["data"]

    first = client.post(f"/api/courses/{c['id']}/reviews", json={"rating": 5, "content": "好"}, headers=h)
    assert first.status_code == 200, first.text
    dup = client.post(f"/api/courses/{c['id']}/reviews", json={"rating": 1, "content": "再评一次"}, headers=h)
    assert dup.status_code == 200
    assert dup.json()["code"] == 40900


def test_course_review_unique_index_blocks_concurrent_insert(client, session_factory):
    """绕过应用层检查的直接双插必须被唯一索引拦下（P1-7 的核心兜底）。

    应用层的 SELECT-then-INSERT 存在竞态窗口，唯一索引才是并发安全的
    最后一道防线 —— 本用例直接向 ORM 塞重复行验证索引真实存在。
    """
    from sqlalchemy.exc import IntegrityError

    from app.modules.course.models import Course, CourseReview

    user = register_login(client, "courseidx1")
    h = auth_header(user["access_token"])
    course = client.post(
        "/api/courses",
        json={"code": "CS301", "name": "编译原理", "teacher": "刘", "credits": 4, "semester": "2025秋"},
        headers=h,
    ).json()["data"]
    client.post(f"/api/courses/{course['id']}/reviews", json={"rating": 5, "content": "首评"}, headers=h)

    async def _dup_insert():
        factory = session_factory
        async with factory() as db:
            from sqlalchemy import select

            cid = (await db.scalar(select(Course.id).where(Course.code == "CS301")))
            db.add(CourseReview(course_id=str(cid), user_id=user["user_id"], rating=1, content="并发插入"))
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                raise

    with pytest.raises(IntegrityError):
        run_async(_dup_insert())


def test_canteen_stall_dish_review(client, session_factory):
    # 食堂 / 摊位 / 菜品由管理端维护，普通用户只能浏览与评价。
    # （这些端点迁到 /api/admin/* 后，本用例曾因仍在公开路径创建而失败）
    seed_admin(session_factory)
    admin_h = admin_login(client)
    user = register_login(client, "canteenuser1")
    h = auth_header(user["access_token"])

    canteen = client.post(
        "/api/admin/canteens", json={"name": "一食堂", "location": "东区"}, headers=admin_h
    ).json()["data"]
    stall = client.post(
        "/api/admin/canteens/stalls",
        json={"canteen_id": canteen["id"], "name": "麻辣档"},
        headers=admin_h,
    ).json()["data"]
    dish = client.post(
        "/api/admin/canteens/dishes",
        json={"stall_id": stall["id"], "name": "麻辣烫", "price": 1500},
        headers=admin_h,
    ).json()["data"]

    rev = client.post(
        f"/api/canteens/dishes/{dish['id']}/reviews",
        json={"rating": 4, "content": "挺好吃的"},
        headers=h,
    )
    assert rev.status_code == 200
    assert rev.json()["data"]["rating"] == 4


def test_course_list_endpoint(client):
    user = register_login(client, "courselist1")
    h = auth_header(user["access_token"])
    client.post(
        "/api/courses",
        json={"code": "MATH101", "name": "高等数学", "teacher": "王", "credits": 4, "semester": "2025秋"},
        headers=h,
    )
    r = client.get("/api/courses", headers=h)
    assert r.status_code == 200
    assert r.json()["code"] == 0
    assert r.json()["data"]["total"] >= 1


def test_canteen_list_and_dish_detail(client, session_factory):
    seed_admin(session_factory)
    admin_h = admin_login(client)
    user = register_login(client, "canteenlist1")
    h = auth_header(user["access_token"])
    canteen = client.post(
        "/api/admin/canteens", json={"name": "二食堂", "location": "西区"}, headers=admin_h
    ).json()["data"]
    stall = client.post(
        "/api/admin/canteens/stalls",
        json={"canteen_id": canteen["id"], "name": "面档"},
        headers=admin_h,
    ).json()["data"]
    dish = client.post(
        "/api/admin/canteens/dishes",
        json={"stall_id": stall["id"], "name": "牛肉面", "price": 1800},
        headers=admin_h,
    ).json()["data"]

    r = client.get("/api/canteens", headers=h)
    assert r.status_code == 200
    assert r.json()["data"][0]["name"] == "二食堂"

    # 菜品详情会调用 list_reviews（曾因 CanteenReviewOut 未导入而 500）
    d = client.get(f"/api/canteens/dishes/{dish['id']}", headers=h)
    assert d.status_code == 200
    assert d.json()["data"]["dish"]["name"] == "牛肉面"

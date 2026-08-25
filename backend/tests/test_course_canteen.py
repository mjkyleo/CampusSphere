"""课程 / 食堂测试：课程评价、食堂-摊位-菜品-评价链路。"""

from __future__ import annotations

from helpers import auth_header, register_login


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


def test_canteen_stall_dish_review(client):
    user = register_login(client, "canteenuser1")
    h = auth_header(user["access_token"])

    canteen = client.post(
        "/api/canteens", json={"name": "一食堂", "location": "东区"}, headers=h
    ).json()["data"]
    stall = client.post(
        "/api/canteens/stalls", json={"canteen_id": canteen["id"], "name": "麻辣档"}, headers=h
    ).json()["data"]
    dish = client.post(
        "/api/canteens/dishes",
        json={"stall_id": stall["id"], "name": "麻辣烫", "price": 1500},
        headers=h,
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


def test_canteen_list_and_dish_detail(client):
    user = register_login(client, "canteenlist1")
    h = auth_header(user["access_token"])
    canteen = client.post("/api/canteens", json={"name": "二食堂", "location": "西区"}, headers=h).json()["data"]
    stall = client.post("/api/canteens/stalls", json={"canteen_id": canteen["id"], "name": "面档"}, headers=h).json()["data"]
    dish = client.post("/api/canteens/dishes", json={"stall_id": stall["id"], "name": "牛肉面", "price": 1800}, headers=h).json()["data"]

    r = client.get("/api/canteens", headers=h)
    assert r.status_code == 200
    assert r.json()["data"][0]["name"] == "二食堂"

    # 菜品详情会调用 list_reviews（曾因 CanteenReviewOut 未导入而 500）
    d = client.get(f"/api/canteens/dishes/{dish['id']}", headers=h)
    assert d.status_code == 200
    assert d.json()["data"]["dish"]["name"] == "牛肉面"

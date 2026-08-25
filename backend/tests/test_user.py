"""用户资料测试：获取 / 更新个人资料并验证持久化。"""

from __future__ import annotations

from helpers import auth_header, register_login


def test_profile_update_and_persist(client):
    user = register_login(client, "profileuser1", nickname="初始昵称")
    h = auth_header(user["access_token"])

    r = client.patch(
        "/api/users/me",
        json={"nickname": "新昵称", "bio": "爱学习", "school_major": "大数据"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["nickname"] == "新昵称"
    assert body["bio"] == "爱学习"

    # 再次获取，确认已持久化
    r2 = client.get("/api/users/me", headers=h)
    assert r2.status_code == 200
    assert r2.json()["data"]["nickname"] == "新昵称"
    assert r2.json()["data"]["school_major"] == "大数据"

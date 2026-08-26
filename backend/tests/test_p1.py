"""P1 模块测试：兼职、资源共享、队友招募、举报、管理后台。"""

from __future__ import annotations

import uuid

from app.core.config import settings
from helpers import auth_header, register_login, run_async


def test_job_create_and_list(client):
    user = register_login(client, "jobuser1")
    h = auth_header(user["access_token"])
    r = client.post(
        "/api/jobs",
        json={"title": "图书馆助理", "description": "整理图书", "company": "校图书馆", "salary": 2000, "category": "campus"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["title"] == "图书馆助理"

    lst = client.get("/api/jobs", headers=h)
    assert lst.status_code == 200
    assert lst.json()["data"]["total"] >= 1


def test_share_create_and_list(client):
    user = register_login(client, "shareuser1")
    h = auth_header(user["access_token"])
    r = client.post(
        "/api/shares",
        json={"title": "考研资料", "description": "数学真题", "file_key": "misc/kaoyan.pdf", "category": "study"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["title"] == "考研资料"

    lst = client.get("/api/shares", headers=h)
    assert lst.status_code == 200
    assert lst.json()["data"]["total"] >= 1


def test_teammate_create_and_list(client):
    user = register_login(client, "teamuser1")
    h = auth_header(user["access_token"])
    r = client.post(
        "/api/teams",
        json={"title": "数学建模队", "description": "招队友", "required_roles": "编程"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["title"] == "数学建模队"

    lst = client.get("/api/teams", headers=h)
    assert lst.status_code == 200
    assert lst.json()["data"]["total"] >= 1


def test_report_submit(client):
    user = register_login(client, "reportuser1")
    h = auth_header(user["access_token"])
    r = client.post(
        "/api/reports",
        json={"target_type": "item", "target_id": str(uuid.uuid4()), "reason": "违规内容"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] is not None


def test_admin_login_dashboard_and_lists(client, session_factory):
    # 测试库未跑 lifespan，需手动 seed 默认管理员
    async def _seed():
        async with session_factory() as db:
            from app.modules.admin.service import ensure_seed

            await ensure_seed(db)

    run_async(_seed())

    r = client.post(
        "/api/admin/login",
        json={
            "username": settings.admin_bootstrap_username,
            "password": settings.admin_bootstrap_password or "admin123",
        },
    )
    assert r.status_code == 200, r.text
    token = r.json()["data"]["access_token"]
    h = auth_header(token)

    dash = client.get("/api/admin/dashboard", headers=h)
    assert dash.status_code == 200
    assert "users" in dash.json()["data"]

    users = client.get("/api/admin/users", headers=h)
    assert users.status_code == 200

    reports = client.get("/api/admin/reports", headers=h)
    assert reports.status_code == 200

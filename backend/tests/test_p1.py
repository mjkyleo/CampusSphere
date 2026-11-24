"""P1 模块测试：兼职、资源共享、队友招募、举报、管理后台。"""

from __future__ import annotations

import uuid

from helpers import admin_login, auth_header, register_login, run_async, seed_admin, user_key

from app.core.config import settings


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
        json={"title": "考研资料", "description": "数学真题", "file_key": user_key(user["user_id"], ".pdf"), "category": "study"},
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


def test_report_duplicate_submission_rejected(client):
    """同一举报人对同一目标重复举报 → 409（P1-9：唯一索引兜底）。"""
    user = register_login(client, "reportdup1")
    h = auth_header(user["access_token"])
    payload = {"target_type": "item", "target_id": str(uuid.uuid4()), "reason": "违规内容"}
    r1 = client.post("/api/reports", json=payload, headers=h)
    assert r1.status_code == 200, r1.text
    r2 = client.post("/api/reports", json=payload, headers=h)
    assert r2.json()["code"] == 40900, r2.text


def test_report_target_type_is_constrained(client):
    """target_type 收敛为封闭枚举：未知类型 → 校验失败（P1-9）。"""
    user = register_login(client, "reporttype1")
    r = client.post(
        "/api/reports",
        json={"target_type": "galaxy", "target_id": str(uuid.uuid4()), "reason": "离谱举报"},
        headers=auth_header(user["access_token"]),
    )
    assert r.json()["code"] != 0, r.text


def test_auto_ban_needs_distinct_reporters(client):
    """auto-ban 口径（P1-9）：同一人重复举报只算一票。

    阈值 5：同一举报人把同一目标举报 N 次（重复的转 409，仅 1 条有效），
    不应触发自动封禁。
    """
    from app.core.config import settings

    target = register_login(client, "autobantarget1")
    spammer = register_login(client, "autobanspam1")
    h = auth_header(spammer["access_token"])
    payload = {"target_type": "user", "target_id": target["user_id"], "reason": "灌水举报"}

    old_policy = settings.report_policy
    settings.report_policy = {**(old_policy or {}), "auto_ban_threshold": 5}
    try:
        for _ in range(8):
            r = client.post("/api/reports", json=payload, headers=h)
            assert r.status_code == 200, r.text
            assert r.json()["code"] in (0, 40900), r.text

        # 目标未被封禁：仍可正常访问需登录接口
        me = client.get("/api/users/me", headers=auth_header(target["access_token"]))
        assert me.status_code == 200 and me.json()["code"] == 0, me.text
    finally:
        settings.report_policy = old_policy


def test_auto_ban_ignores_rejected_reports(client, session_factory):
    """auto-ban 口径（P1-9）：管理员驳回的举报不再计数。

    阈值 5：2 条被驳回 + 4 条有效（distinct 举报人）→ 不封禁；
    再来第 5 个有效举报人 → 封禁。
    """
    from app.core.config import settings

    seed_admin(session_factory)
    admin_h = admin_login(client)

    target = register_login(client, "autobantarget2")
    reporters = [register_login(client, f"autobanrep{i}") for i in range(7)]

    def _report(u):
        return client.post(
            "/api/reports",
            json={"target_type": "user", "target_id": target["user_id"], "reason": "违规"},
            headers=auth_header(u["access_token"]),
        )

    old_policy = settings.report_policy
    settings.report_policy = {**(old_policy or {}), "auto_ban_threshold": 5}
    try:
        # 前两名举报后由管理员驳回 → 不应计入，且同一人无法对同一目标重复举报
        for u in reporters[:2]:
            r = _report(u)
            assert r.json()["code"] == 0, r.text
            rid = r.json()["data"]["id"]
            rj = client.post(
                f"/api/reports/{rid}/handle",
                json={"action": "reject", "note": "证据不足"},
                headers=admin_h,
            )
            assert rj.status_code == 200, rj.text

        # 4 名有效举报人（distinct）→ 未达阈值，不封禁
        for u in reporters[2:6]:
            assert _report(u).json()["code"] == 0
        me = client.get("/api/users/me", headers=auth_header(target["access_token"]))
        assert me.json()["code"] == 0, "4 名不同举报人不应触发自动封禁"

        # 第 5 名有效举报人（此前 2 条已驳回不计）→ 达到阈值 → 封禁
        assert _report(reporters[6]).json()["code"] == 0
        me2 = client.get("/api/users/me", headers=auth_header(target["access_token"]))
        assert me2.json()["code"] != 0, "有效举报达到阈值后应自动封禁"
    finally:
        settings.report_policy = old_policy


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

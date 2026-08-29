"""管理后台内容治理集成测试：**管理员登录 → 查看举报 → 处理工单 → 封禁**。

已知缺陷（以 xfail 固化，见下方两条 ``xfail`` 用例）
------------------------------------------------
``/api/reports/*`` 仅依赖 ``get_current_user``，**未校验管理员身份**，
而管理网关中间件只保护 ``/api/admin/*``。结果是任意登录用户都能：

* 查看全部举报工单（信息泄露）；
* 处置任意工单，包括用 ``action="ban"`` 封禁任意用户（**越权提权**）。

修复方向：给 report 路由的 ``handle`` / ``list_all`` 加上
``Depends(require_admin)``（该依赖已存在于 ``app.modules.admin.deps``）。
"""

from __future__ import annotations

import pytest

from app.common.enums import ReportStatus, UserStatus
from factories import ReportFactory
from helpers import admin_login, auth_header, register_login, seed_admin

pytestmark = pytest.mark.integration


@pytest.fixture
def admin_headers(client, session_factory):
    """播种并登录管理员，返回可用的管理员请求头。"""
    seed_admin(session_factory)
    return admin_login(client)


async def _seed_report(fx, reporter_id: str, target_id: str, target_type: str = "user"):
    return await fx.create(
        ReportFactory,
        reporter_id=reporter_id,
        target_id=target_id,
        target_type=target_type,
        reason="发布违规内容",
    )


# ---------------------------------------------------------------------------
# 管理员正常流程
# ---------------------------------------------------------------------------
async def test_admin_lists_reports(client, fx, admin_headers):
    """管理员可查看举报工单列表（旅程：查看举报列表）。"""
    reporter = register_login(client, "mod_reporter")
    target = register_login(client, "mod_target")
    report = await _seed_report(fx, reporter["user_id"], target["user_id"])

    r = client.get("/api/admin/reports", headers=admin_headers)
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    assert report.id in [x["id"] for x in r.json()["data"]["items"]]


async def test_admin_can_filter_pending_reports(client, fx, admin_headers):
    """按状态筛选：待处理工单。"""
    reporter = register_login(client, "mod_reporter2")
    target = register_login(client, "mod_target2")
    report = await _seed_report(fx, reporter["user_id"], target["user_id"])

    r = client.get(
        "/api/admin/reports",
        params={"status": ReportStatus.PENDING.value},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert report.id in [x["id"] for x in r.json()["data"]["items"]]


@pytest.mark.xfail(
    reason="已知缺陷 P0：举报处置链路双重失效 —— "
    "(1) /api/reports/{id}/handle 依赖 get_current_user（查 users 表），"
    "管理员令牌属于 AdminUser 表，反被判'用户不存在'，管理员无法处置工单；"
    "(2) 该端点又完全不校验管理员身份，任意普通用户均可处置并封禁他人。"
    "修复：改用 require_admin 依赖（见 docs/TESTING.md）",
    strict=False,
)
async def test_admin_resolves_report(client, fx, admin_headers):
    """管理员处理工单（旅程：处理工单）→ 状态变为已处理。"""
    reporter = register_login(client, "mod_reporter3")
    target = register_login(client, "mod_target3")
    report = await _seed_report(fx, reporter["user_id"], target["user_id"])

    r = client.post(
        f"/api/reports/{report.id}/handle",
        json={"action": "resolve", "note": "已核实并警告"},
        headers=admin_headers,
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    assert r.json()["data"]["status"] == ReportStatus.RESOLVED.value


@pytest.mark.xfail(
    reason="同 test_admin_resolves_report：处置端点身份体系错配，管理员令牌无法调用",
    strict=False,
)
async def test_admin_rejects_report(client, fx, admin_headers):
    """管理员可驳回工单 → 状态变为已驳回。"""
    reporter = register_login(client, "mod_reporter4")
    target = register_login(client, "mod_target4")
    report = await _seed_report(fx, reporter["user_id"], target["user_id"])

    r = client.post(
        f"/api/reports/{report.id}/handle",
        json={"action": "reject", "note": "举报不成立"},
        headers=admin_headers,
    )
    assert r.json()["code"] == 0
    assert r.json()["data"]["status"] == ReportStatus.REJECTED.value


async def test_admin_bans_user(client, admin_headers):
    """管理员封禁用户 → 用户状态变为封禁。"""
    victim = register_login(client, "mod_victim")
    r = client.post(
        f"/api/admin/users/{victim['user_id']}/ban",
        json={"reason": "多次违规"},
        headers=admin_headers,
    )
    assert r.status_code == 200 and r.json()["code"] == 0, r.text
    assert r.json()["data"]["status"] == UserStatus.BANNED.value


async def test_banned_user_cannot_login(client, admin_headers):
    """被封禁用户无法登录（封禁真正生效）。"""
    victim = register_login(client, "mod_victim2")
    client.post(
        f"/api/admin/users/{victim['user_id']}/ban",
        json={"reason": "违规"},
        headers=admin_headers,
    )

    r = client.post("/api/auth/login", json={"username": "mod_victim2", "password": "secret123"})
    assert r.json()["code"] != 0
    assert "封禁" in r.json()["message"]


async def test_admin_unbans_user(client, admin_headers):
    """解封后用户可以重新登录。"""
    victim = register_login(client, "mod_victim3")
    client.post(
        f"/api/admin/users/{victim['user_id']}/ban", json={"reason": "违规"}, headers=admin_headers
    )
    unban = client.post(
        f"/api/admin/users/{victim['user_id']}/unban", headers=admin_headers
    )
    assert unban.json()["code"] == 0

    r = client.post("/api/auth/login", json={"username": "mod_victim3", "password": "secret123"})
    assert r.json()["code"] == 0


# ---------------------------------------------------------------------------
# 权限边界
# ---------------------------------------------------------------------------
async def test_admin_endpoints_require_authentication(client):
    """未携带令牌访问管理端 → 401。"""
    r = client.get("/api/admin/reports")
    assert r.status_code == 401


async def test_ordinary_user_cannot_access_admin_reports(client):
    """普通用户令牌访问 ``/api/admin/*`` → 被拒绝（管理网关生效）。"""
    user = register_login(client, "mod_normal")
    r = client.get("/api/admin/reports", headers=auth_header(user["access_token"]))
    assert r.status_code in (401, 403) or r.json()["code"] != 0


# ---------------------------------------------------------------------------
# 已知缺陷（xfail：缺陷修复后会自动转为 XPASS 提示更新）
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    reason="安全缺陷 P0：/api/reports/{id}/handle 未校验管理员身份，"
    "任意登录用户可处置工单并用 action=ban 封禁他人（见 docs/TESTING.md）",
    strict=False,
)
async def test_ordinary_user_cannot_handle_report(client, fx, admin_headers):
    """普通用户**不应**能处置举报工单（当前实现允许 → 越权）。"""
    reporter = register_login(client, "mod_reporter5")
    target = register_login(client, "mod_target5")
    attacker = register_login(client, "mod_attacker5")
    report = await _seed_report(fx, reporter["user_id"], target["user_id"])

    r = client.post(
        f"/api/reports/{report.id}/handle",
        json={"action": "ban", "note": "越权封禁"},
        headers=auth_header(attacker["access_token"]),
    )
    assert r.json()["code"] != 0, "普通用户成功处置了工单（应为越权失败）"


@pytest.mark.xfail(
    reason="安全缺陷 P0：GET /api/reports 未校验管理员身份，任意登录用户可查看全部举报",
    strict=False,
)
async def test_ordinary_user_cannot_list_all_reports(client, fx, admin_headers):
    """普通用户**不应**能查看全部举报工单（当前实现允许 → 信息泄露）。"""
    reporter = register_login(client, "mod_reporter6")
    target = register_login(client, "mod_target6")
    outsider = register_login(client, "mod_outsider6")
    await _seed_report(fx, reporter["user_id"], target["user_id"])

    r = client.get("/api/reports", headers=auth_header(outsider["access_token"]))
    assert r.json()["code"] != 0, "普通用户看到了全部举报工单"

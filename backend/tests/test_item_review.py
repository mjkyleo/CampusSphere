"""T4.3 发布审核开关测试。

覆盖：默认（关闭）发布即上架；开启后新发布进入待审核(PENDING=4)，
广场/他人详情不可见，管理员通过后上架、拒绝后下架，关闭后恢复直接上架。
"""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.modules.admin.service import ensure_seed
from helpers import auth_header, register_login


def _seed_admin(test_engine) -> None:
    async def _run():
        factory = async_sessionmaker(
            bind=test_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with factory() as db:
            await ensure_seed(db)

    asyncio.run(_run())


def _admin_token(client) -> str:
    r = client.post(
        "/api/admin/login",
        json={
            "username": settings.admin_bootstrap_username,
            "password": settings.admin_bootstrap_password or "admin123",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["code"] == 0
    return r.json()["data"]["access_token"]


def _set_review(client, enabled: bool) -> None:
    token = _admin_token(client)
    r = client.put(
        "/api/admin/items/review-config",
        json={"enabled": enabled},
        headers=auth_header(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["enabled"] is enabled


def _create_item(client, token, title="审核测试物品"):
    r = client.post(
        "/api/items",
        json={
            "title": title,
            "description": "九成新",
            "price": 9900,
            "category": "bike",
            "images": [{"object_key": "misc/rv1.bin", "sort_order": 0}],
        },
        headers=auth_header(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["code"] == 0
    return r.json()["data"]


def test_review_disabled_by_default(client, test_engine):
    """默认（开关未配置）：发布即上架(0)，广场可见。"""
    _seed_admin(test_engine)
    user = register_login(client, "rvuser1")
    item = _create_item(client, user["access_token"])
    assert item["status"] == 0

    r = client.get("/api/items", headers=auth_header(user["access_token"]))
    assert item["id"] in [i["id"] for i in r.json()["data"]["items"]]


def test_review_enabled_flow(client, test_engine):
    """开启审核：发布进入 PENDING；他人列表/详情不可见；管理员通过后上架可见。"""
    _seed_admin(test_engine)
    _set_review(client, True)

    owner = register_login(client, "rvowner")
    viewer = register_login(client, "rvviewer")
    item = _create_item(client, owner["access_token"])
    assert item["status"] == 4  # PENDING

    # 他人列表不可见（广场过滤 PENDING）
    r = client.get("/api/items", headers=auth_header(viewer["access_token"]))
    assert item["id"] not in [i["id"] for i in r.json()["data"]["items"]]

    # 他人详情视为不存在
    r2 = client.get(f"/api/items/{item['id']}", headers=auth_header(viewer["access_token"]))
    assert r2.status_code == 200
    assert r2.json()["code"] != 0

    # 本人详情可见且标记待审核
    r3 = client.get(f"/api/items/{item['id']}", headers=auth_header(owner["access_token"]))
    assert r3.status_code == 200
    assert r3.json()["data"]["status"] == 4

    # 管理员通过 → 上架，他人可见
    admin_token = _admin_token(client)
    ra = client.post(
        f"/api/admin/items/{item['id']}/approve", headers=auth_header(admin_token)
    )
    assert ra.status_code == 200, ra.text
    assert ra.json()["data"]["status"] == 0
    r4 = client.get("/api/items", headers=auth_header(viewer["access_token"]))
    assert item["id"] in [i["id"] for i in r4.json()["data"]["items"]]


def test_review_reject_flow(client, test_engine):
    """审核拒绝：PENDING → OFF_SHELF；关闭开关后新发布直接上架。"""
    _seed_admin(test_engine)
    _set_review(client, True)

    owner = register_login(client, "rvo2")
    item = _create_item(client, owner["access_token"])
    assert item["status"] == 4

    admin_token = _admin_token(client)
    r = client.post(
        f"/api/admin/items/{item['id']}/reject",
        json={"reason": "内容不符合平台规范"},
        headers=auth_header(admin_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == 1  # OFF_SHELF

    # 关闭审核后新发布直接上架
    _set_review(client, False)
    item2 = _create_item(client, owner["access_token"], title="关闭后发布")
    assert item2["status"] == 0

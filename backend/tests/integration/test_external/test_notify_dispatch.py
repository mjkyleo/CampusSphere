"""站内通知派发集成测试。

验证交易创建、入队申请、兼职申请三个业务事件发生后，都会向
``app.tasks.notify.send_notify`` 发起 ``.delay()`` 调用。

真实 Celery broker 未启动，因此用 monkeypatch 替换任务对象，只断言派发契约；
任务体的 Redis 发布语义由 ``tests/unit/test_notify_unit.py`` 单独覆盖。
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from helpers import auth_header, register_login

pytestmark = pytest.mark.integration


@pytest.fixture
def notify_task(monkeypatch):
    """将 ``send_notify`` 替换为 MagicMock，返回 mock 供断言。"""
    mock = MagicMock()
    monkeypatch.setattr("app.tasks.notify.send_notify", mock)
    return mock


def test_trade_session_sends_notify_to_seller(client, notify_task):
    """买家对物品发起交易，卖家应收到站内通知。"""
    seller_name, buyer_name = "notify_seller", "notify_buyer"
    seller = register_login(client, seller_name)
    buyer = register_login(client, buyer_name)

    r = client.post(
        "/api/items",
        json={
            "title": "通知测试书",
            "description": "九成新",
            "price": 1000,
            "category": "book",
            "images": [],
        },
        headers=auth_header(seller["access_token"]),
    )
    assert r.status_code == 200, r.text
    item = r.json()["data"]

    r2 = client.post(
        f"/api/items/{item['id']}/trade",
        headers=auth_header(buyer["access_token"]),
    )
    assert r2.status_code == 200, r2.text

    notify_task.delay.assert_called_once()
    args, kwargs = notify_task.delay.call_args
    assert args[0] == seller["user_id"]  # target user_id
    assert "想购买" in args[1]
    assert buyer_name in args[2]
    assert item["title"] in args[2]
    assert kwargs.get("channel") == "inapp"


def test_join_team_sends_notify_to_creator(client, notify_task):
    """用户申请加入队伍，队长应收到站内通知。"""
    creator_name, joiner_name = "notify_team_creator", "notify_team_joiner"
    creator = register_login(client, creator_name)
    joiner = register_login(client, joiner_name)

    r = client.post(
        "/api/teams",
        json={
            "title": "通知测试小队",
            "description": "一起参加比赛",
            "required_roles": "后端",
            "category": "竞赛",
        },
        headers=auth_header(creator["access_token"]),
    )
    assert r.status_code == 200, r.text
    team = r.json()["data"]

    r2 = client.post(
        f"/api/teams/{team['id']}/join",
        json={"role": "后端"},
        headers=auth_header(joiner["access_token"]),
    )
    assert r2.status_code == 200, r2.text

    notify_task.delay.assert_called_once()
    args, kwargs = notify_task.delay.call_args
    assert args[0] == creator["user_id"]
    assert joiner_name in args[1]
    assert team["title"] in args[1]
    assert "后端" in args[2]
    assert kwargs.get("channel") == "inapp"


def test_apply_job_sends_notify_to_poster(client, notify_task):
    """用户申请兼职，发布者应收到站内通知。"""
    poster_name, applicant_name = "notify_job_poster", "notify_job_applicant"
    poster = register_login(client, poster_name)
    applicant = register_login(client, applicant_name)

    r = client.post(
        "/api/jobs",
        json={
            "title": "通知测试兼职",
            "description": "发传单",
            "company": "测试公司",
            "salary": 100,
            "category": "other",
        },
        headers=auth_header(poster["access_token"]),
    )
    assert r.status_code == 200, r.text
    job = r.json()["data"]

    r2 = client.post(
        f"/api/jobs/{job['id']}/apply",
        json={"note": "我可以"},
        headers=auth_header(applicant["access_token"]),
    )
    assert r2.status_code == 200, r2.text

    notify_task.delay.assert_called_once()
    args, kwargs = notify_task.delay.call_args
    assert args[0] == poster["user_id"]
    assert applicant_name in args[1]
    assert job["title"] in args[1]
    assert kwargs.get("channel") == "inapp"

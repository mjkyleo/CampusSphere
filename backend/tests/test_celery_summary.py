"""Celery 交易会话摘要任务测试。

通过直接调用任务函数（而非 broker 分发）验证聚合逻辑与缓存行为；
数据库访问经 monkeypatch 指向测试库（sync_session_factory）。
"""

from __future__ import annotations

import uuid

import pytest
from helpers import auth_header, register_login

from app.tasks.summary import generate_trade_summary


def _create_trade(client):
    """创建一笔交易会话，返回 trade 响应 data。"""
    seller = register_login(client, "sumseller")
    buyer = register_login(client, "sumbuyer")
    r = client.post(
        "/api/items",
        json={
            "title": "摘要测试书本",
            "description": "九成新",
            "price": 2000,
            "category": "book",
            "images": [{"object_key": "misc/sum1.bin", "sort_order": 0}],
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
    return r2.json()["data"]


def test_generate_trade_summary(ws_client, sync_session_factory, monkeypatch):
    """正常路径：摘要聚合字段完整且与交易数据一致。"""
    trade = _create_trade(ws_client)
    monkeypatch.setattr("app.tasks.summary.get_session_factory", lambda: sync_session_factory)

    result = generate_trade_summary(str(trade["id"]))

    assert result["trade_id"] == str(trade["id"])
    assert result["buyer_id"] == trade["buyer_id"]
    assert result["seller_id"] == trade["seller_id"]
    assert result["item_id"] == str(trade["item_id"])
    assert result["item_title"] == "摘要测试书本"
    assert result["price"] == 2000
    assert result["status"] == trade["status"]
    assert result["message_count"] == 0
    assert result["generated_at"]


def test_generate_trade_summary_uses_cache_and_force(ws_client, sync_session_factory, monkeypatch):
    """缓存命中返回相同结果；force=True 时强制重新生成。"""
    trade = _create_trade(ws_client)
    monkeypatch.setattr("app.tasks.summary.get_session_factory", lambda: sync_session_factory)
    trade_id = str(trade["id"])

    first = generate_trade_summary(trade_id)
    second = generate_trade_summary(trade_id)  # 命中缓存
    assert second == first

    forced = generate_trade_summary(trade_id, force=True)
    assert forced["trade_id"] == first["trade_id"]
    assert forced["generated_at"] != first["generated_at"]


def test_generate_trade_summary_missing_trade(ws_client, sync_session_factory, monkeypatch):
    """交易会话不存在时抛出 ValueError。"""
    monkeypatch.setattr("app.tasks.summary.get_session_factory", lambda: sync_session_factory)

    with pytest.raises(ValueError, match="交易会话不存在"):
        generate_trade_summary(str(uuid.uuid4()))

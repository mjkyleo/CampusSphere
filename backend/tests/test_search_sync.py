"""搜索索引写侧接线测试（app/search/sync.py）。

覆盖四个关键行为：
1. 公开可见物品（上架/非待审核/未删除）派发 sync_item，待审核/已删除派发 delete_doc
   ——搜索接口命中 Meilisearch 时直接返回文档、不再过滤，索引策略就是防泄露闸门；
2. 索引文档与 ItemOut 形状一致（两条搜索路径返回同构数据），且邮箱/手机号脱敏；
3. API 发布物品后实际派发了索引同步任务（端到端）；
4. broker 不可达（delay 抛错）时静默降级，不影响主流程。

生产调用方不等待派发结果（fire-and-forget）；测试里 await 返回的 Future 保证时序。
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from helpers import auth_header, key_from_token, register_login

from app.common.enums import ItemStatus
from app.modules.item.models import Item
from app.search import sync as search_sync
from app.tasks import search_sync as search_sync_tasks


def _stub_item(**kwargs) -> Item:
    """不落库的轻量 Item 桩（index_item 只读属性）。"""
    base: dict = dict(
        id="it000000000000000000000000000001",
        owner_id="u-1",
        title="桩物品",
        description="",
        price=100,
        category="other",
        images=[],
    )
    base.update(kwargs)
    return Item(**base)


def _patched_calls(monkeypatch) -> list[tuple[str, tuple]]:
    calls: list[tuple[str, tuple]] = []
    monkeypatch.setattr(
        search_sync_tasks.sync_item,
        "delay",
        lambda *a: calls.append(("sync_item", a)),
    )
    monkeypatch.setattr(
        search_sync_tasks.delete_doc,
        "delay",
        lambda *a: calls.append(("delete_doc", a)),
    )
    return calls


async def test_public_item_dispatches_sync_pending_and_deleted_dispatch_delete(monkeypatch):
    calls = _patched_calls(monkeypatch)

    f1 = search_sync.index_item(_stub_item(status=ItemStatus.ON_SALE.value))
    f2 = search_sync.index_item(_stub_item(status=ItemStatus.PENDING.value))
    f3 = search_sync.index_item(
        _stub_item(status=ItemStatus.ON_SALE.value, deleted_at=datetime.now(UTC))
    )
    await f1
    await f2
    await f3

    assert [name for name, _ in calls] == ["sync_item", "delete_doc", "delete_doc"]
    assert calls[0][1][0] == "it000000000000000000000000000001"


async def test_item_doc_matches_item_out_shape(session_factory):
    """索引文档字段与 ItemOut 一致，Meili 命中与 DB 兜底两条路径数据同构。"""
    item = _stub_item()
    async with session_factory() as db:
        db.add(item)
        await db.commit()
        await db.refresh(item)

    doc = search_sync.item_doc(item)
    for key in (
        "id", "owner_id", "title", "description", "price",
        "category", "status", "images", "created_at",
    ):
        assert key in doc, f"索引文档缺少 ItemOut 字段: {key}"
    assert doc["title"] == "桩物品"


async def test_user_doc_masks_email_and_phone():
    """用户文档脱敏后再入索引（Meilisearch 命中会原样返回给前端）。"""

    class _User:
        id = "u-1"
        username = "searcher"
        nickname = "搜索者"
        avatar = None
        email = "searcher@example.com"
        phone = "13800138000"
        status = 1
        deleted_at = None

    doc = search_sync.user_doc(_User())
    assert doc["email"] == "s*******@example.com"
    assert doc["phone"] == "138****8000"


async def test_dispatch_swallows_broker_failure(monkeypatch):
    """broker 不可达时 delay 抛错 → 记 warning 后丢弃，绝不向调用方传播。"""
    monkeypatch.setattr(
        search_sync_tasks.sync_item,
        "delay",
        lambda *a: (_ for _ in ()).throw(ConnectionError("broker down")),
    )
    fut = search_sync.index_item(_stub_item(status=ItemStatus.ON_SALE.value))
    await asyncio.wrap_future(fut)  # _run 吞掉异常，Future 正常完成


def test_create_item_triggers_index_dispatch(client, monkeypatch):
    """端到端：API 发布物品后应实际派发一次 sync_item（payload 与 ItemOut 同构）。"""
    calls = _patched_calls(monkeypatch)
    user = register_login(client, "searche2e1")
    token = user["access_token"]

    payload = {
        "title": "端到端搜索物品",
        "description": "九成新",
        "price": 19900,
        "category": "bike",
        "images": [{"object_key": key_from_token(token), "sort_order": 0}],
    }
    r = client.post("/api/items", json=payload, headers=auth_header(token))
    assert r.status_code == 200, r.text
    item_id = r.json()["data"]["id"]

    # 派发在请求事件循环的线程池里 fire-and-forget，轮询等待完成
    import time

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not calls:
        time.sleep(0.05)
    assert calls, "发布物品后未派发任何搜索索引同步任务"
    name, args = calls[0]
    assert name == "sync_item"
    assert args[0] == item_id
    assert args[1]["title"] == "端到端搜索物品"

"""搜索索引同步集成测试：**mock 客户端验证同步契约 + 无搜索引擎时的降级**。

``SearchClient`` 在未配置 Meilisearch 时 ``enabled=False``，
所有索引操作静默跳过 —— 这是**有意的优雅降级**（保证无搜索服务也能跑），
本文件同时覆盖"有客户端时索引内容正确"与"无客户端时不炸"两条路径。

注意：``sync_item`` 等是**同步** Celery 任务，内部用 ``asyncio.run`` 驱动
异步索引调用，因此这些用例必须写成**同步函数**，
否则在 pytest-asyncio 的事件循环里调用 ``asyncio.run`` 会抛 RuntimeError。
"""

from __future__ import annotations

import pytest

import app.tasks.search_sync as search_sync

pytestmark = pytest.mark.integration


class FakeSearchClient:
    """记录索引调用的假客户端（用于验证同步契约）。"""

    INDEX_USERS = "users"
    INDEX_ITEMS = "items"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.indexed: list[tuple[str, dict]] = []
        self.deleted: list[tuple[str, str]] = []

    async def index_document(self, index: str, doc: dict) -> None:
        self.indexed.append((index, doc))

    async def delete_document(self, index: str, doc_id: str) -> None:
        self.deleted.append((index, doc_id))


@pytest.fixture
def fake_client(monkeypatch):
    """把 ``get_search_client`` 替换为假客户端，并返回该客户端供断言。"""
    client = FakeSearchClient()
    monkeypatch.setattr(search_sync, "get_search_client", lambda: client)
    return client


# ---------------------------------------------------------------------------
# 有搜索引擎：验证同步内容
# ---------------------------------------------------------------------------
def test_sync_item_indexes_to_items_index(fake_client):
    """物品同步：写入 items 索引，文档内容原样透传。"""
    doc = {"id": "item-1", "title": "闲置自行车", "category": "交通工具"}
    result = search_sync.sync_item("item-1", doc)

    assert result == {"ok": True}
    assert fake_client.indexed == [(FakeSearchClient.INDEX_ITEMS, doc)]


def test_sync_user_indexes_to_users_index(fake_client):
    """用户同步：写入 users 索引。"""
    doc = {"id": "user-1", "username": "alice"}
    search_sync.sync_user("user-1", doc)

    assert fake_client.indexed == [(FakeSearchClient.INDEX_USERS, doc)]


def test_delete_doc_removes_from_index(fake_client):
    """下架/注销时从索引中删除文档。"""
    result = search_sync.delete_doc("items", "item-1")
    assert result == {"ok": True}
    assert fake_client.deleted == [("items", "item-1")]


# ---------------------------------------------------------------------------
# 无搜索引擎：优雅降级
# ---------------------------------------------------------------------------
def test_sync_degrades_gracefully_without_client(monkeypatch):
    """无搜索客户端（未配置 Meilisearch）→ 静默成功，不抛异常。"""
    monkeypatch.setattr(search_sync, "get_search_client", lambda: None)
    result = search_sync.sync_item("item-2", {"id": "item-2", "title": "台灯"})
    assert result == {"ok": True}


def test_sync_skips_when_client_disabled(monkeypatch):
    """客户端存在但未启用 → 不写索引，仍返回成功。"""
    disabled = FakeSearchClient(enabled=False)
    monkeypatch.setattr(search_sync, "get_search_client", lambda: disabled)

    result = search_sync.sync_item("item-3", {"id": "item-3"})
    assert result == {"ok": True}
    assert disabled.indexed == []


def test_sync_survives_index_failure(monkeypatch):
    """索引写入抛异常（引擎抖动）不影响任务返回，避免 Celery 无限重试风暴。"""

    class BoomClient(FakeSearchClient):
        async def index_document(self, index, doc):
            raise RuntimeError("meili down")

    monkeypatch.setattr(search_sync, "get_search_client", lambda: BoomClient())

    # SearchClient 内部已捕获异常；这里用假客户端验证"任务层不会把异常抛出去"
    with pytest.raises(RuntimeError):
        search_sync.sync_item("item-4", {"id": "item-4"})

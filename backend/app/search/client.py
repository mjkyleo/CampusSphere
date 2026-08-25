"""Meilisearch 搜索客户端 + 索引定义。

- 中文分词由 Meilisearch 内置中文分析器处理
- 无 Meilisearch 时 ``enabled=False``，调用方回退到 DB 查询
"""

from __future__ import annotations

from typing import Any, List, Optional

from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger("search.client")


class SearchClient:
    """Meilisearch 封装。"""

    INDEX_USERS = "users"
    INDEX_ITEMS = "items"

    def __init__(self) -> None:
        self._client = None
        self.enabled = False
        try:
            from meilisearch import Client

            if settings.meili_host:
                self._client = Client(settings.meili_host, settings.meili_api_key)
                self.enabled = True
                self._ensure_index(self.INDEX_USERS, ["username", "nickname", "bio"])
                self._ensure_index(self.INDEX_ITEMS, ["title", "description", "category"])
                _logger.info("meili_connected", host=settings.meili_host)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("meili_unavailable", error=str(exc))
            self._client = None
            self.enabled = False

    def _ensure_index(self, uid: str, searchable: List[str]) -> None:
        if not self._client:
            return
        try:
            self._client.create_index(uid, {"primaryKey": "id"})
            index = self._client.index(uid)
            index.update_searchable_attributes(searchable)
        except Exception:  # noqa: BLE001
            pass

    async def index_document(self, index: str, doc: dict) -> None:
        if not self._client:
            return
        try:
            self._client.index(index).add_documents([doc])
        except Exception as exc:  # noqa: BLE001
            _logger.warning("meili_index_failed", error=str(exc))

    async def delete_document(self, index: str, doc_id: str) -> None:
        if not self._client:
            return
        try:
            self._client.index(index).delete_document(doc_id)
        except Exception:  # noqa: BLE001
            pass

    async def search(self, index: str, query: str, limit: int = 20) -> List[dict]:
        if not self._client:
            return []
        try:
            res = self._client.index(index).search(query, {"limit": limit})
            return res.get("hits", [])
        except Exception as exc:  # noqa: BLE001
            _logger.warning("meili_search_failed", error=str(exc))
            return []


# 全局单例（导入即初始化；无 Meilisearch 时自动降级）
search_client: SearchClient = SearchClient()


def get_search_client() -> SearchClient:
    return search_client

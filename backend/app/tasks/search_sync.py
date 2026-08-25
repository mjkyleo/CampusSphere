"""搜索索引同步任务（Meilisearch）。"""

from __future__ import annotations

from app.core.logging import get_logger
from app.search.client import get_search_client
from app.tasks.celery_app import celery_app

_logger = get_logger("tasks.search_sync")


@celery_app.task(name="app.tasks.search_sync.sync_user", bind=True, max_retries=3)
def sync_user(self, user_id: str, doc: dict):
    client = get_search_client()
    if client and client.enabled:
        import asyncio

        asyncio.run(client.index_document(client.INDEX_USERS, doc))
    _logger.info("user_synced", user_id=user_id)
    return {"ok": True}


@celery_app.task(name="app.tasks.search_sync.sync_item", bind=True, max_retries=3)
def sync_item(self, item_id: str, doc: dict):
    client = get_search_client()
    if client and client.enabled:
        import asyncio

        asyncio.run(client.index_document(client.INDEX_ITEMS, doc))
    _logger.info("item_synced", item_id=item_id)
    return {"ok": True}


@celery_app.task(name="app.tasks.search_sync.delete_doc", bind=True, max_retries=3)
def delete_doc(self, index: str, doc_id: str):
    client = get_search_client()
    if client and client.enabled:
        import asyncio

        asyncio.run(client.delete_document(index, doc_id))
    return {"ok": True}

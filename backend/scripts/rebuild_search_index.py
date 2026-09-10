"""Meilisearch 索引全量重建脚本。

用法（项目根目录或 backend 目录均可）::

    python backend/scripts/rebuild_search_index.py [items|users]

默认重建 ``items`` 索引。脚本会：
1. 清空目标索引；
2. 从数据库全量读取符合条件的记录；
3. 调用 Celery 任务批量写入 Meilisearch。

注意：本脚本需要在能访问 Meilisearch 与数据库的环境中运行（如后端容器内或本地
开发环境）。索引重建期间搜索服务可能短暂不完整，建议在低峰期执行。
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.sync_db import get_session_factory
from app.modules.item.models import Item
from app.modules.item.service import item_search_doc
from app.search.client import SearchClient, get_search_client
from app.tasks.search_sync import sync_item

configure_logging()
_logger = get_logger("scripts.rebuild_search_index")


_TYPE_MAP: dict[str, tuple[str, type]] = {
    "items": (SearchClient.INDEX_ITEMS, Item),
}


def _rebuild_items(client: SearchClient) -> dict[str, Any]:
    """重建 items 索引：只同步在售且未软删除的物品。"""
    index_name = client.INDEX_ITEMS
    client._client.index(index_name).delete_all_documents()

    factory = get_session_factory()
    with factory() as db:
        rows = db.scalars(
            select(Item).where(Item.status == 0, Item.deleted_at.is_(None))
        ).all()

    sent = 0
    for item in rows:
        # 复用 Service 层的文档构造逻辑，避免两份字段定义漂移
        doc = item_search_doc(item)
        sync_item.delay(str(item.id), doc)
        sent += 1

    return {"index": index_name, "sent": sent}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild Meilisearch index")
    parser.add_argument(
        "target",
        nargs="?",
        default="items",
        choices=list(_TYPE_MAP.keys()),
        help="要重建的索引类型（默认 items）",
    )
    args = parser.parse_args(argv)

    client = get_search_client()
    if not client or not client.enabled:
        _logger.error("meilisearch_not_available", host=settings.meili_host)
        print("Meilisearch 不可用，请检查 MEILI_HOST / MEILI_API_KEY 配置。")
        return 1

    _logger.info("rebuild_search_index_start", target=args.target)

    if args.target == "items":
        result = _rebuild_items(client)
    else:
        # 预留 users 索引的扩展入口
        print(f"暂不支持的索引类型: {args.target}")
        return 1

    _logger.info(
        "rebuild_search_index_done",
        target=args.target,
        index=result["index"],
        sent=result["sent"],
    )
    print(f"已发送 {result['sent']} 条 {result['index']} 索引同步任务到 Celery 队列。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

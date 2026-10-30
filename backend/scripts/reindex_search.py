"""全量重建 Meilisearch 搜索索引（一次性运维脚本）。

使用场景
--------
* 首次部署后把存量数据灌入索引（增量同步只覆盖发布/更新之后的变化）；
* 更换 / 清空 Meilisearch 实例后恢复索引；
* 索引与数据库出现漂移时的修复手段。

用法（backend 目录下，且 Meilisearch 可达）::

    python -m scripts.reindex_search           # 重建 items + users
    python -m scripts.reindex_search --only items

幂等：按文档主键覆盖写入，重复执行安全。脚本只索引公开可见记录
（物品排除待审核/已删除，用户排除已注销），与线上增量同步策略一致，
见 app/search/sync.py。
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core.logging import get_logger
from app.search.client import search_client
from app.search.sync import item_doc, user_doc

_logger = get_logger("scripts.reindex_search")


async def reindex_items() -> int:
    from app.common.enums import ItemStatus
    from app.core.database import SessionLocal
    from app.modules.item.models import Item

    count = 0
    async with SessionLocal() as db:
        rows = await db.scalars(
            select(Item).where(
                Item.deleted_at.is_(None), Item.status != ItemStatus.PENDING.value
            )
        )
        for item in rows:
            await search_client.index_document(search_client.INDEX_ITEMS, item_doc(item))
            count += 1
    return count


async def reindex_users() -> int:
    from app.core.database import SessionLocal
    from app.modules.auth.models import User

    count = 0
    async with SessionLocal() as db:
        rows = await db.scalars(select(User).where(User.deleted_at.is_(None)))
        for user in rows:
            await search_client.index_document(search_client.INDEX_USERS, user_doc(user))
            count += 1
    return count


async def main() -> None:
    parser = argparse.ArgumentParser(description="重建 Meilisearch 搜索索引")
    parser.add_argument("--only", choices=["items", "users"], default=None)
    args = parser.parse_args()

    if not search_client.enabled:
        raise SystemExit(
            "Meilisearch 未启用：请配置 MEILI_HOST 后重试"
            "（未启用时搜索自动走 DB LIKE 兜底，索引非必需）"
        )

    if args.only in (None, "items"):
        n = await reindex_items()
        print(f"items indexed: {n}")
    if args.only in (None, "users"):
        n = await reindex_users()
        print(f"users indexed: {n}")
    _logger.info("reindex_completed")


if __name__ == "__main__":
    asyncio.run(main())

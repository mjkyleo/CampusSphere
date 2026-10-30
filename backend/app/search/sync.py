"""搜索索引写侧同步（读侧封装在 app/search/client.py）。

为何经 Celery 派发
------------------
Meilisearch Python 客户端是同步 IO，若在 async 请求处理里直接调用会把
事件循环整个堵住；复用与 email 任务相同的 worker 基础设施，让索引写入
异步化、可重试。

最佳努力语义
------------
搜索查询侧有 DB LIKE 兜底（client.enabled=False 或索引未命中时自动回退），
因此派发失败只记 warning，绝不影响发布/更新主流程。

索引可见性策略
--------------
搜索接口（GET /api/items/search）命中 Meilisearch 时直接返回文档、不再过
滤状态，因此**只允许公开可见的记录进索引**：物品排除"待审核(PENDING)"与
已软删除，用户排除已注销——否则未审核内容会经由搜索泄露。
"""

from __future__ import annotations

import asyncio
from concurrent.futures import Future

from app.core.logging import get_logger

_logger = get_logger("search.sync")


def _dispatch(task_name: str, send) -> Future:
    """在线程池里派发 Celery 任务并立即返回（调用方无需等待）。

    ``delay()`` 是同步阻塞调用，绝不能出现在事件循环线程里（与
    auth.service 的邮件派发同理）；broker 连接超时被压到 1 秒，派发失败
    （本地无 Redis / 队列抖动）时降级为跳过——搜索有 LIKE 兜底，可安全丢弃。

    返回 executor Future 仅供测试断言用；生产调用方一律不 await。
    """

    def _run() -> None:
        try:
            send()
        except Exception as exc:
            _logger.warning("search_sync_dispatch_failed", task=task_name, error=str(exc))

    return asyncio.get_running_loop().run_in_executor(None, _run)


def item_doc(item) -> dict:
    """把 Item ORM 对象序列化成与 ItemOut 同构的索引文档。

    字段形状与 GET /api/items 列表返回一致，保证 Meilisearch 命中与 DB
    兜底两条路径交给前端的数据结构相同。
    """
    return {
        "id": str(item.id),
        "owner_id": str(item.owner_id),
        "title": item.title,
        "description": item.description,
        "price": item.price,
        "category": item.category,
        "status": item.status,
        "images": [
            {"id": str(i.id), "object_key": i.object_key, "sort_order": i.sort_order}
            for i in item.images
        ],
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def user_doc(user) -> dict:
    """用户索引文档（字段与 user.service.list_users 返回一致，脱敏后再进索引）。"""
    from app.common.utils import mask_email, mask_phone

    return {
        "id": str(user.id),
        "username": user.username,
        "nickname": user.nickname,
        "avatar": user.avatar,
        "email": mask_email(user.email),
        "phone": mask_phone(user.phone) if user.phone else None,
        "status": user.status,
    }


def index_item(item) -> Future:
    """物品公开可见（非待审核、未删除）时写索引，否则从索引移除。"""
    from app.common.enums import ItemStatus
    from app.tasks import search_sync

    if item.deleted_at is not None or item.status == ItemStatus.PENDING.value:
        return remove_item(item)
    return _dispatch(
        "app.tasks.search_sync.sync_item",
        lambda: search_sync.sync_item.delay(str(item.id), item_doc(item)),
    )


def remove_item(item) -> Future:
    from app.tasks import search_sync

    return _dispatch(
        "app.tasks.search_sync.delete_doc",
        lambda: search_sync.delete_doc.delay("items", str(item.id)),
    )


def index_user(user) -> Future:
    from app.tasks import search_sync

    if user.deleted_at is not None:
        return remove_user(user)
    return _dispatch(
        "app.tasks.search_sync.sync_user",
        lambda: search_sync.sync_user.delay(str(user.id), user_doc(user)),
    )


def remove_user(user) -> Future:
    from app.tasks import search_sync

    return _dispatch(
        "app.tasks.search_sync.delete_doc",
        lambda: search_sync.delete_doc.delay("users", str(user.id)),
    )

"""Celery 应用实例（Redis broker + 重试/死信配置）。"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger("tasks.celery")

# --- Redis Lock 无 Lua 兼容（本地开发用 fakeredis 等不支持 Lua 的服务端）---
# kombu 的 redis transport 在 restore_visible 时使用 redis-py 的 Lock，
# 其 release 默认通过 Lua 脚本（EVALSHA）做 token 校验删除；
# fakeredis 不执行 Lua 脚本，这里替换为 WATCH/MULTI 事务实现。
import redis as _redis_module
from redis.lock import Lock as _RedisLock


def _compat_lock_release(self, expected_token=None):
    token = expected_token
    if token is None:
        token = getattr(getattr(self, "local", None), "token", None)
    if token:
        with self.redis.pipeline() as pipe:
            try:
                pipe.watch(self.name)
                if pipe.get(self.name) == token:
                    pipe.multi()
                    pipe.delete(self.name)
                    pipe.execute()
                else:
                    pipe.unwatch()
            except _redis_module.WatchError:
                pass
    else:
        self.redis.delete(self.name)


if getattr(_RedisLock, "do_release", None) is not None:
    _RedisLock.do_release = _compat_lock_release

celery_app = Celery(
    "campus",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=4,
    task_default_queue="default",
    task_routes={
        "app.tasks.email.*": {"queue": "email"},
        "app.tasks.notify.*": {"queue": "notify"},
        "app.tasks.search_sync.*": {"queue": "search"},
    },
    # 重试策略（指数退避，最多 3 次）
    task_annotations={
        "*": {
            "max_retries": 3,
            "retry_backoff": True,
            "retry_backoff_max": 600,
            "retry_jitter": True,
        }
    },
)

# 自动发现任务模块
celery_app.autodiscover_tasks(["app.tasks"])

_logger.info("celery_app_initialized", broker=settings.celery_broker_url)

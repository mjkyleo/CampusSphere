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
import redis as _redis_module  # noqa: E402 - 与下方兼容补丁同组，需置于 _logger 之后
from redis.lock import Lock as _RedisLock  # noqa: E402


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
    # 结果后端禁用：本平台的任务（邮件/通知/搜索同步）全部是"发完即忘"，
    # 从不调用 ``.get()`` 读取任务结果。保留 redis 结果后端会让 ``delay()`` 在派发前
    # 经 ``backend.on_task_call`` 连接结果库，不可达时按默认策略同步重试约 20 次
    # （≈ 109 秒），把调用线程卡死、整站无响应。禁用后该连接彻底跳过，
    # broker 不可达时 ``delay()`` 立即抛错，由调用方降级为内联直发。
    backend="disabled://",
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
    # ----- broker 连接快速失败 -----
    # 本地未起 Redis / 生产 broker 抖动时，若让 Celery 按默认策略同步重试
    # （约 20 次 × 1 秒 ≈ 2 分钟），会长时间阻塞调用线程、甚至占满线程池。
    # 这里把连接超时压到 1 秒，让 ``delay()`` 在 broker 不可达时快速抛错，
    # 由调用方降级为内联直发（见 auth.service._dispatch_code_email）。
    broker_connection_max_retries=2,
    broker_connection_retry=True,
    broker_connection_retry_policy={
        "max_retries": 2,
        "interval_start": 0.1,
        "interval_step": 0.2,
        "interval_max": 0.5,
    },
    broker_transport_options={
        "socket_timeout": 1,
        "socket_connect_timeout": 1,
        "retry_on_timeout": True,
    },
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

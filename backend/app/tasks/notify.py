"""站内/短信通知任务。"""

from __future__ import annotations

from app.core.logging import get_logger
from app.core.redis import redis_publish
from app.tasks.celery_app import celery_app

_logger = get_logger("tasks.notify")


@celery_app.task(name="app.tasks.notify.send_notify", bind=True, max_retries=3)
def send_notify(self, user_id: str, title: str, content: str, channel: str = "inapp"):
    """发送通知（inapp：经 Redis Pub/Sub 推送到 WS；sms：接入短信服务商）。"""
    try:
        if channel == "inapp":
            import json

            payload = {
                "event": "notify",
                "data": {"user_id": user_id, "title": title, "content": content},
            }
            # 通知频道与 WS 广播同机制
            import asyncio

            asyncio.run(redis_publish(f"notify:{user_id}", json.dumps(payload, default=str)))
        _logger.info("notify_sent", user_id=user_id, channel=channel)
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        _logger.error("notify_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=10)

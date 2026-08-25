"""邮件发送任务（失败重试 + 死信）。"""

from __future__ import annotations

from typing import Optional

from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

_logger = get_logger("tasks.email")


@celery_app.task(name="app.tasks.email.send_email", bind=True, max_retries=3)
def send_email(self, to: str, subject: str, body: str, html: Optional[str] = None):
    """发送邮件（示例：通过 SMTP/邮件服务商 API；此处以日志占位，便于接 SES/阿里云）。"""
    try:
        # TODO: 接入真实邮件服务商（SES / 阿里云邮件推送）
        _logger.info("email_send_attempt", to=to, subject=subject)
        # 模拟发送成功
        return {"ok": True, "to": to}
    except Exception as exc:  # noqa: BLE001
        _logger.error("email_send_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=10)


@celery_app.task(name="app.tasks.email.send_welcome", bind=True, max_retries=3)
def send_welcome(self, to: str, nickname: str = ""):
    return send_email(to, "欢迎加入校园生活平台", f"Hi {nickname}，欢迎使用校园生活平台！")

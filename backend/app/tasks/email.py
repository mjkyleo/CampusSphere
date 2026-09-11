"""邮件发送任务（失败重试 + 死信）。

实现说明
--------
底层走 ``smtplib`` 直连 SMTP 服务商：

* 465 端口默认 **SSL 直连**（``SMTP_SSL``）；
* 其余端口（常见 587）走 **STARTTLS** 升级；
* 可用 ``SMTP_STARTTLS=true/false`` 强制覆盖端口推断。

这是一个 **同步阻塞** 调用，因此必须设置超时上限（``SMTP_TIMEOUT``），
避免 SMTP 服务不可用时把 Celery worker 的连接/线程拖死。

未配置 ``SMTP_HOST`` 时任务**不会**谎报成功，而是返回
``{"ok": False, reason: "smtp_not_configured"}`` —— 让"邮件没发出去"
在日志与监控里可见，而不是伪装成已送达。
"""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings
from app.core.logging import get_logger
from app.tasks.celery_app import celery_app

_logger = get_logger("tasks.email")


def _build_message(to: str, subject: str, body: str, html: str | None = None) -> EmailMessage:
    """构造邮件：纯文本为正文，html 作为可选替代视图。"""
    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    return msg


def _deliver(to: str, subject: str, body: str, html: str | None = None) -> None:
    """实际投递。按端口选择 SSL 直连或 STARTTLS。"""
    msg = _build_message(to, subject, body, html)
    timeout = settings.smtp_timeout
    # 端口推断：465 是 SMTPS（SSL 直连），587/25 等则需 STARTTLS 升级
    use_starttls = (settings.smtp_port != 465) if settings.smtp_starttls is None else settings.smtp_starttls

    if use_starttls:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout) as server:
            server.starttls(context=ssl.create_default_context())
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_pass)
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(
            settings.smtp_host, settings.smtp_port, timeout=timeout, context=ssl.create_default_context()
        ) as server:
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_pass)
            server.send_message(msg)


@celery_app.task(name="app.tasks.email.send_email", bind=True, max_retries=3)
def send_email(self, to: str, subject: str, body: str, html: str | None = None):
    """发送邮件；SMTP 未配置时明确返回失败，不伪装成功。"""
    if not settings.smtp_host:
        # 不重试：配置缺失重试也无意义，重试只会堆积无用队列
        _logger.warning("email_not_sent_smtp_unconfigured", to=to, subject=subject)
        return {"ok": False, "to": to, "sent": False, "reason": "smtp_not_configured"}

    try:
        _deliver(to, subject, body, html)
    except Exception as exc:
        _logger.error("email_send_failed", to=to, error=str(exc))
        raise self.retry(exc=exc, countdown=10) from exc

    _logger.info("email_sent", to=to, subject=subject)
    return {"ok": True, "to": to, "sent": True}


@celery_app.task(name="app.tasks.email.send_welcome", bind=True, max_retries=3)
def send_welcome(self, to: str, nickname: str = ""):
    return send_email(to, "欢迎加入校园生活平台", f"Hi {nickname}，欢迎使用校园生活平台！")

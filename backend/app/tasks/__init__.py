"""Celery 异步任务包：邮件、通知、搜索同步、交易摘要。

注意：必须在此显式导入各任务模块，确保 ``autodiscover_tasks`` 能注册到
worker。否则任务装饰器永远不会执行，``celery_app.tasks`` 为空，
worker 收到消息后无法执行任何任务。
"""

from app.tasks import email, notify, search_sync, summary

__all__ = ["email", "notify", "search_sync", "summary"]

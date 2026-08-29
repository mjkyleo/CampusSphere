"""结构化日志（structlog -> JSON stdout）。

- 每条请求经中间件写入 ``request_id``（X-Request-ID）。
- 敏感字段（手机号/邮箱/密码）在日志中脱敏。
- logger 命名空间统一 ``campus.<module>``。
"""

from __future__ import annotations

import logging

import structlog

_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    """初始化 structlog + 标准 logging。幂等。"""
    global _configured
    if _configured:
        return
    logging.basicConfig(format="%(message)s", level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str):
    """获取统一命名空间的 logger。"""
    if not _configured:
        configure_logging()
    return structlog.get_logger(f"campus.{name}")


def bind_request(request_id: str, user_id: str | None = None) -> None:
    """在请求中间件中绑定上下文变量。"""
    structlog.contextvars.bind_contextvars(request_id=request_id)
    if user_id:
        structlog.contextvars.bind_contextvars(user_id=user_id)


def clear_request() -> None:
    structlog.contextvars.clear_contextvars()

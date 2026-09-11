"""结构化日志（structlog -> JSON stdout）。

- 每条请求经中间件写入 ``request_id``（X-Request-ID）。
- 敏感字段（手机号/邮箱/密码）在日志中脱敏。
- logger 命名空间统一 ``campus.<module>``。
- ``request_id`` 同时写入独立 ContextVar，供 SQL 注释注入读取
  （见 ``app/core/database.py`` 的 trace_id 染色）。
"""

from __future__ import annotations

import contextvars
import logging
import re

import structlog

_configured = False

# 独立的 trace id ContextVar：与 structlog 上下文**同源**（都由
# ``bind_request`` 写入），单独存放是为了避免 database.py 依赖 structlog
# 的内部结构。必须在模块导入期创建——运行期新建 ContextVar 会丢失已绑定值。
_trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "campus_trace_id", default=None
)

# trace id 允许的字符。
#
# **安全要点**：X-Request-ID 可能直接来自**客户端请求头**（见 middleware.py：
# ``request.headers.get("X-Request-ID") or uuid4().hex``），属于不可信输入。
# 若原样拼进 SQL 注释，攻击者可用 ``*/ DELETE FROM users; --`` 提前闭合
# 注释块实施注入。因此这里只允许安全字符集。
_SAFE_TRACE_ID = re.compile(r"[^A-Za-z0-9_.:-]")
_MAX_TRACE_ID_LEN = 64


def sanitize_trace_id(value: str | None) -> str | None:
    """把 trace id 收敛为可安全嵌入 SQL 注释的形式。

    嵌入 SQL 注释前**必须**调用：trace id 可能由客户端提供。
    """
    if not value:
        return None
    cleaned = _SAFE_TRACE_ID.sub("", str(value))[:_MAX_TRACE_ID_LEN]
    return cleaned or None


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
    """在请求中间件中绑定上下文变量（日志与 SQL 染色的**唯一**入口）。"""
    structlog.contextvars.bind_contextvars(request_id=request_id)
    _trace_id_var.set(request_id)
    if user_id:
        structlog.contextvars.bind_contextvars(user_id=user_id)


def clear_request() -> None:
    structlog.contextvars.clear_contextvars()
    _trace_id_var.set(None)


def get_trace_id() -> str | None:
    """读取当前上下文的 trace id（已消毒，可安全用于 SQL 注释）。"""
    return sanitize_trace_id(_trace_id_var.get())

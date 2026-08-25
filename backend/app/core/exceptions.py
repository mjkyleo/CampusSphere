"""统一异常体系：BizError + FastAPI 异常处理注册。

所有业务错误抛 ``BizError(code, message, status)``，由 ``register_exception_handlers``
在应用工厂中注册，包装成 ``ApiResponse``；404/422/500 同样统一包装。
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.core.response import ApiResponse

_logger = get_logger("core.exceptions")


class BizError(Exception):
    """业务异常。``code`` 为业务码（非 0），``status`` 为 HTTP 状态码。"""

    def __init__(self, code: int, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


# 常用业务错误码
class ErrorCode:
    BAD_REQUEST = 40000
    UNAUTHORIZED = 40100
    FORBIDDEN = 40300
    NOT_FOUND = 40400
    CONFLICT = 40900
    VALIDATION = 42200
    TOO_MANY_REQUESTS = 42900
    INTERNAL = 50000


def _wrap(code: int, message: str, status: int) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ApiResponse(code=code, message=message, data=None).model_dump(),
    )


async def biz_error_handler(_: Request, exc: BizError) -> JSONResponse:
    _logger.warning("biz_error", code=exc.code, message=exc.message)
    # 统一响应约定：业务错误一律以 HTTP 200 返回，业务状态码由响应体中的 code 承载，
    # 与网关中间件返回的 401/403 等框架级状态码区分开。
    return _wrap(exc.code, exc.message, 200)


async def validation_error_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    details = exc.errors()
    msg = "参数校验失败"
    if details:
        msg = f"{details[0].get('loc', ['?'])[-1]}: {details[0].get('msg', '')}"
    return _wrap(ErrorCode.VALIDATION, msg, 422)


async def not_found_handler(_: Request, exc: Exception) -> JSONResponse:
    return _wrap(ErrorCode.NOT_FOUND, "资源不存在", 404)


async def server_error_handler(_: Request, exc: Exception) -> JSONResponse:
    _logger.error("server_error", error=str(exc))
    return _wrap(ErrorCode.INTERNAL, "服务器内部错误", 500)


def register_exception_handlers(app: FastAPI) -> None:
    """在应用工厂中注册所有统一异常处理。"""
    app.add_exception_handler(BizError, biz_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(404, not_found_handler)
    app.add_exception_handler(500, server_error_handler)

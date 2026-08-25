"""统一响应包装 ``ApiResponse``。

全站所有 REST 接口返回 ``ApiResponse[data=...].model_dump()``，成功 code=0。
异常由 ``app.core.exceptions`` 的 handler 统一包装为 ``ApiResponse``。
"""

from __future__ import annotations

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应体。"""

    code: int = 0
    message: str = "ok"
    data: Optional[T] = None

    @classmethod
    def ok(cls, data: Optional[T] = None, message: str = "ok") -> "ApiResponse[T]":
        return cls(code=0, message=message, data=data)

    @classmethod
    def fail(cls, code: int, message: str) -> "ApiResponse[None]":
        return cls(code=code, message=message, data=None)


def success(data: Optional[T] = None, message: str = "ok") -> dict:
    """便捷函数：返回可直接 Response 的 dict。"""
    return ApiResponse[object].ok(data=data, message=message).model_dump()


def fail(code: int, message: str) -> dict:
    return ApiResponse[None].fail(code=code, message=message).model_dump()

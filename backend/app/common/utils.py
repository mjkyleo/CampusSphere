"""通用工具函数：分页、手机号/邮箱脱敏、雪花 ID 等。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")

_PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_phone(value: str) -> bool:
    """校验中国大陆手机号。"""
    return bool(_PHONE_RE.match(value or ""))


def is_valid_email(value: str) -> bool:
    """校验邮箱格式。"""
    return bool(_EMAIL_RE.match(value or ""))


def mask_phone(phone: Optional[str]) -> Optional[str]:
    """手机号脱敏：138****8000。"""
    if not phone:
        return phone
    if len(phone) == 11:
        return f"{phone[:3]}****{phone[7:]}"
    return f"{phone[:3]}***{phone[-2:]}"


def mask_email(email: Optional[str]) -> Optional[str]:
    """邮箱脱敏：a***@example.com。"""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}{'*' * (len(local) - 1)}@{domain}"


@dataclass
class Page:
    """分页参数。"""

    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (max(self.page, 1) - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass
class PageResult(Generic[T]):
    """分页结果封装。"""

    items: List[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    def to_dict(self, item_mapper=lambda x: x) -> Dict[str, Any]:
        return {
            "items": [item_mapper(i) for i in self.items],
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "pages": self.pages,
        }


def generate_code(length: int = 6) -> str:
    """生成数字验证码。"""
    import random

    return "".join(random.choice("0123456789") for _ in range(length))


def safe_int(value: Any, default: int = 0) -> int:
    """安全转 int。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

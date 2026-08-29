"""全局枚举与状态机取值。

所有状态的整型取值与 ARCHITECTURE.md 第 3.2 节保持一致：
- users.status：0正常/1封禁/2待审核
- items.status：0上架/1下架/2已售/3保留
- messages.type：0文本/1图片/2文件
"""

from __future__ import annotations

from enum import IntEnum, StrEnum


class UserStatus(IntEnum):
    """用户状态。"""

    NORMAL = 0
    BANNED = 1
    PENDING = 2


class ItemStatus(IntEnum):
    """二手物品状态机取值。

    PENDING(4) 为"待审核"态：当后台开启发布审核开关（items.review.enabled）
    后，新发布物品进入该状态，管理员审核通过后流转到 ON_SALE。
    """

    ON_SALE = 0
    OFF_SHELF = 1
    SOLD = 2
    RESERVED = 3
    PENDING = 4


class TradeStatus(IntEnum):
    """交易会话状态。"""

    PENDING = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    CANCELLED = 3


class MessageType(IntEnum):
    """消息类型。"""

    TEXT = 0
    IMAGE = 1
    FILE = 2


class JobStatus(IntEnum):
    """兼职岗位状态。"""

    OPEN = 0
    CLOSED = 1


class ApplicationStatus(IntEnum):
    """兼职申请状态。"""

    PENDING = 0
    ACCEPTED = 1
    REJECTED = 2


class TeamStatus(IntEnum):
    """招募团队状态。"""

    RECRUITING = 0
    FULL = 1
    DISBANDED = 2


class MemberStatus(IntEnum):
    """团队成员状态。"""

    PENDING = 0
    ACTIVE = 1
    LEFT = 2


class ReportStatus(IntEnum):
    """举报工单状态。"""

    PENDING = 0
    REVIEWING = 1
    RESOLVED = 2
    REJECTED = 3


class ReportTargetType(StrEnum):
    """举报目标类型。"""

    USER = "user"
    ITEM = "item"
    MESSAGE = "message"
    COMMENT = "comment"
    SHARE = "share"


class ConversationType(StrEnum):
    """会话类型。"""

    DIRECT = "direct"
    TRADE = "trade"
    GROUP = "group"

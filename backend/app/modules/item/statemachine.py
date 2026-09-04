"""二手物品状态机：上架/下架/已售/保留 的合法流转。"""

from __future__ import annotations

from app.common.enums import ItemStatus
from app.core.exceptions import BizError, ErrorCode

# 允许的状态迁移：from -> set(to)
TRANSITIONS: dict[ItemStatus, set[ItemStatus]] = {
    ItemStatus.ON_SALE: {ItemStatus.OFF_SHELF, ItemStatus.RESERVED, ItemStatus.SOLD},
    ItemStatus.OFF_SHELF: {ItemStatus.ON_SALE},
    # 被预订（RESERVED）的物品仍可下架（卖家取消交易 / 买家反悔），
    # 也可回到上架或成交。下架是合法出口，否则会出现"卡在预订态无法下掉"的死锁。
    ItemStatus.RESERVED: {ItemStatus.ON_SALE, ItemStatus.SOLD, ItemStatus.OFF_SHELF},
    ItemStatus.SOLD: set(),  # 终态
    ItemStatus.PENDING: {ItemStatus.ON_SALE, ItemStatus.OFF_SHELF},  # 审核通过/拒绝
}


def can_transition(current: int, target: int) -> bool:
    cur = ItemStatus(current)
    tgt = ItemStatus(target)
    return tgt in TRANSITIONS.get(cur, set())


def validate_transition(current: int, target: int) -> None:
    if not can_transition(current, target):
        raise BizError(
            ErrorCode.VALIDATION,
            f"非法状态流转：{ItemStatus(current).name} -> {ItemStatus(target).name}",
        )


def next_status_on_sold() -> int:
    return ItemStatus.SOLD.value

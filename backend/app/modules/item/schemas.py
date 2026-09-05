"""二手物品模块 Pydantic 模型（富领域模型：业务规则前置）。

设计原则：把业务规则从 Service 层**左移**到类型系统
--------------------------------------------------
校验不再只是"字段是否为空"，而是"这条数据是否是一笔合法的业务"。
Pydantic 的解析过程因此成为**第一道防线**：非法数据在进入 Service 之前
就被拒绝，Service 只需处理"已经合法"的输入。

金额契约（重要）
----------------
``price`` 的单位**恒定为「分」的整数**，与前端 ``toCents()`` 对齐
（见 ``frontend/services/api.ts``）。后端**不做**元→分转换，因为前端
已完成转换 —— 若后端再乘一次 100，12.50 元会变成 125000 分（即 1250 元），
是典型的**双重转换**数据事故。

本模块要防的是另一类事故：Pydantic 在 lax 模式下会把 ``12.0`` / ``"12"``
静默转成 ``12``，更糟的是把 ``True`` 转成 ``1``（bool 是 int 的子类）——
``{"price": true}`` 会被当成 1 分写入数据库。因此这里用
``mode="before"`` 的校验器对**原始输入**做类型把关，确保 Service 拿到的
永远是纯整数分。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.common.enums import ItemStatus
from app.core.config import settings

# 价格上限（分）：≈100 万元。防御异常金额（手误多敲几个 0、或被篡改的请求体）
# 污染市集排序与搜索结果。
MAX_PRICE_CENTS = 99_999_900

ELECTRONICS_CATEGORY = "电子产品"


def _rule(name: str, default):
    """读取 ``school.yaml`` 的 ``items.rules`` 业务规则阈值。

    规则阈值外置而非写死在代码里，是为了让运营在**不重新发版**的情况下
    调整严格程度（配合 Task 4 的配置热更新可做到改完即生效）。
    """
    rules = ((settings.items or {}).get("rules") or {})
    return rules.get(name, default)


def _electronics_min_images() -> int:
    """电子产品要求的最少图片数；``0`` 表示该规则未启用。"""
    try:
        return int(_rule("electronics_min_images", 0))
    except (TypeError, ValueError):
        return 0


def _forbid_zero_price_on_sale() -> bool:
    """是否禁止零元挂售。"""
    return bool(_rule("forbid_zero_price_on_sale", True))


def _validate_cents(v: object, field: str = "价格") -> object:
    """金额必须是**纯整数分**：拒绝 bool / 小数 / 字符串。

    使用 ``mode="before"`` 校验器调用，拿到的是**未经 Pydantic 强制转换**的
    原始输入，因此能拦住 lax 模式下会被静默吞掉的几类脏数据：

    * ``12.0``  → 本会被转成 ``12``（掩盖了前端传错单位的问题）
    * ``"12"``  → 本会被转成 ``12``（掩盖了前端未做数值转换的问题）
    * ``True``  → 本会被转成 ``1``（bool 是 int 的子类，最危险的一类）
    """
    # bool 必须在 int 之前判断：isinstance(True, int) 为 True
    if isinstance(v, bool):
        raise ValueError(f"{field}必须是整数（单位：分），不接受布尔值")
    if isinstance(v, float):
        raise ValueError(f"{field}必须是整数（单位：分），不接受小数")
    if isinstance(v, str):
        raise ValueError(f"{field}必须是整数（单位：分），不接受字符串")
    if isinstance(v, int) and v > MAX_PRICE_CENTS:
        raise ValueError(f"{field}超出上限")
    return v


class ItemImageIn(BaseModel):
    object_key: str
    sort_order: int = 0


class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: str = ""
    price: int = Field(default=0, ge=0, description="单位：分")
    category: str = "other"
    images: list[ItemImageIn] = []

    @field_validator("price", mode="before")
    @classmethod
    def _price_must_be_integral_cents(cls, v: object) -> object:
        return _validate_cents(v)

    @model_validator(mode="after")
    def _check_cross_field_rules(self) -> ItemCreate:
        """跨字段业务规则（Pydantic v2 的 model_validator）。

        ``mode="after"`` 下所有字段已完成各自校验，此处可以看到**完整的
        对象状态**，因此适合表达"字段之间的依赖"——这正是单字段校验器
        做不到、过去只能塞进 Service 层的那类规则。
        """
        min_images = _electronics_min_images()
        if (
            min_images > 0
            and self.category == ELECTRONICS_CATEGORY
            and len(self.images) < min_images
        ):
            raise ValueError(f"{ELECTRONICS_CATEGORY}类物品至少需要 {min_images} 张实物图")

        if _forbid_zero_price_on_sale() and self.price == 0:
            raise ValueError("禁止零元发布：请填写价格，或改为赠送/下架")
        return self


class ItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    price: int | None = None
    category: str | None = None
    status: int | None = Field(default=None, description="状态流转目标值")

    @field_validator("price", mode="before")
    @classmethod
    def _price_must_be_integral_cents(cls, v: object) -> object:
        # 部分更新时 price 可不传（None 表示"不修改"），需要显式放行
        if v is None:
            return v
        return _validate_cents(v)

    @model_validator(mode="after")
    def _check_zero_price_on_sale(self) -> ItemUpdate:
        """禁止把物品**改为**在售态的同时把价格设为 0。

        注意边界：部分更新（PATCH）时若未传 ``price``，Schema 无从得知
        数据库中该物品的现有价格，因此**只能校验"本次显式传了 price=0
        且目标状态为在售"**这一种情况。要覆盖"物品本来就是 0 元、只改状态"
        的情况，必须在 Service 层结合当前记录判断 —— 那属于跨请求状态，
        不是纯 Schema 职责。
        """
        if (
            _forbid_zero_price_on_sale()
            and self.price == 0
            and self.status == ItemStatus.ON_SALE.value
        ):
            raise ValueError("禁止零元挂售：在售物品必须填写价格")
        return self


class ItemImageOut(BaseModel):
    id: UUID
    object_key: str
    sort_order: int

    model_config = {"from_attributes": True}


class ItemOut(BaseModel):
    id: UUID
    owner_id: str
    title: str
    description: str
    price: int
    category: str
    status: int
    images: list[ItemImageOut] = []
    created_at: str | None = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _dt_to_str(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = {"from_attributes": True}


class TradeSessionCreate(BaseModel):
    buyer_id: str | None = None  # 不传则取当前用户


class TradeSessionOut(BaseModel):
    id: UUID
    item_id: str
    buyer_id: str
    seller_id: str
    status: int
    conversation_id: str | None = None

    model_config = {"from_attributes": True}

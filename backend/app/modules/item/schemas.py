"""二手物品模块 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ItemImageIn(BaseModel):
    object_key: str
    sort_order: int = 0


class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: str = ""
    price: int = Field(default=0, ge=0, description="单位：分")
    category: str = "other"
    images: List[ItemImageIn] = []


class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    category: Optional[str] = None
    status: Optional[int] = Field(default=None, description="状态流转目标值")


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
    images: List[ItemImageOut] = []
    created_at: Optional[str] = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _dt_to_str(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = {"from_attributes": True}


class TradeSessionCreate(BaseModel):
    buyer_id: Optional[str] = None  # 不传则取当前用户


class TradeSessionOut(BaseModel):
    id: UUID
    item_id: str
    buyer_id: str
    seller_id: str
    status: int
    conversation_id: Optional[str] = None

    model_config = {"from_attributes": True}

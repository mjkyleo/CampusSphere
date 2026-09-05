"""食堂模块 Pydantic 模型。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class CanteenCreate(BaseModel):
    name: str
    location: str = ""
    image: str = ""
    campus: str = ""
    zone: str = ""
    canteen_type: str = ""
    floor: str = ""
    description: str = ""
    features: list[str] = []
    popular_dishes: list[str] = []
    opening_hours: str = ""
    semester: str = ""


class StallCreate(BaseModel):
    canteen_id: str
    name: str
    image: str = ""


class DishCreate(BaseModel):
    stall_id: str
    name: str
    price: int = Field(default=0, ge=0, description="单位：分")
    image: str = ""


class CanteenReviewCreate(BaseModel):
    rating: int = Field(default=5, ge=1, le=5)
    content: str = ""


class DishOut(BaseModel):
    id: UUID
    stall_id: str
    name: str
    price: int
    image: str

    model_config = {"from_attributes": True}


class StallOut(BaseModel):
    id: UUID
    canteen_id: str
    name: str
    image: str
    dishes: list[DishOut] = []

    model_config = {"from_attributes": True}


class CanteenOut(BaseModel):
    id: UUID
    name: str
    location: str
    image: str
    campus: str = ""
    zone: str = ""
    canteen_type: str = ""
    floor: str = ""
    description: str = ""
    features: list[str] = []
    popular_dishes: list[str] = []
    opening_hours: str = ""
    semester: str = ""
    stalls: list[StallOut] = []

    model_config = {"from_attributes": True}


class CanteenReviewOut(BaseModel):
    id: UUID
    dish_id: str
    user_id: str
    rating: int
    content: str

    model_config = {"from_attributes": True}

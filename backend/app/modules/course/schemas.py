"""课程模块 Pydantic 模型。"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CourseCreate(BaseModel):
    code: str
    name: str
    teacher: str = ""
    credits: int = 0
    semester: str = ""


class CourseOut(BaseModel):
    id: UUID
    code: str
    name: str
    teacher: str
    credits: int
    semester: str

    model_config = {"from_attributes": True}


class CourseReviewCreate(BaseModel):
    rating: int = Field(default=5, ge=1, le=5)
    content: str = ""


class CourseReviewOut(BaseModel):
    id: UUID
    course_id: str
    user_id: str
    rating: int
    content: str

    model_config = {"from_attributes": True}

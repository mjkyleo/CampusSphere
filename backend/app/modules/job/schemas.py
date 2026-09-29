"""兼职模块 Pydantic 模型。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    company: str = Field(default="", max_length=128)
    # P2-5：salary 此前接受负数——防手误负号污染排序/展示
    salary: int = Field(default=0, ge=0, le=99_999_900)
    category: str = Field(default="other", max_length=32)


class JobOut(BaseModel):
    id: UUID
    poster_id: str
    title: str
    description: str
    company: str
    salary: int
    category: str
    status: int

    model_config = {"from_attributes": True}


class JobApplicationCreate(BaseModel):
    note: str = Field(default="", max_length=500)


class JobApplicationOut(BaseModel):
    id: UUID
    job_id: str
    applicant_id: str
    status: int
    note: str

    model_config = {"from_attributes": True}

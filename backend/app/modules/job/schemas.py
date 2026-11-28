"""兼职模块 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, computed_field


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    company: str = Field(default="", max_length=128)
    # P2-5：salary 此前接受负数——防手误负号污染排序/展示
    salary: int = Field(default=0, ge=0, le=99_999_900)
    # 前端统一用「分」传薪资金额，兼容历史 salary 字段。
    salary_cents: int | None = Field(default=None, ge=0, le=99_999_900)
    salary_type: int = Field(default=1, ge=0, le=3)
    category: str = Field(default="other", max_length=32)
    location: str = Field(default="", max_length=255)
    contact: str = Field(default="", max_length=255)
    requirements: str = Field(default="", max_length=1000)


class JobOut(BaseModel):
    id: UUID
    poster_id: str
    title: str
    description: str
    company: str
    salary: int
    salary_type: int = 1
    category: str
    status: int
    location: str = ""
    contact: str = ""
    requirements: str = ""
    created_at: datetime | None = None

    @computed_field
    @property
    def salary_cents(self) -> int:
        return self.salary

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

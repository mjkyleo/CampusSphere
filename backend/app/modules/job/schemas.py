"""兼职模块 Pydantic 模型。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: str = ""
    company: str = ""
    salary: int = 0
    category: str = "other"


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
    note: str = ""


class JobApplicationOut(BaseModel):
    id: UUID
    job_id: str
    applicant_id: str
    status: int
    note: str

    model_config = {"from_attributes": True}

"""资源共享 Pydantic 模型。"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ShareCreate(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    description: str = ""
    file_key: str = ""
    category: str = "other"


class ShareOut(BaseModel):
    id: UUID
    owner_id: str
    title: str
    description: str
    file_key: str
    category: str
    downloads: int
    download_url: Optional[str] = None

    model_config = {"from_attributes": True}

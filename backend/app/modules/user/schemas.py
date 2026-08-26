"""用户模块 Pydantic 模型。"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ProfileUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    school_major: Optional[str] = None
    campus: Optional[str] = None
    contact_wx: Optional[str] = None
    grade: Optional[int] = None


class UserProfileOut(BaseModel):
    id: UUID
    user_id: str
    username: str
    nickname: str
    avatar: Optional[str] = None
    bio: str
    school_major: str
    campus: str
    contact_wx: str
    grade: int
    verified: bool
    email: Optional[str] = None
    phone: Optional[str] = None

    model_config = {"from_attributes": True}

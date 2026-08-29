"""用户模块 Pydantic 模型。"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ProfileUpdateRequest(BaseModel):
    nickname: str | None = None
    avatar: str | None = None
    bio: str | None = None
    school_major: str | None = None
    campus: str | None = None
    contact_wx: str | None = None
    grade: int | None = None


class UserProfileOut(BaseModel):
    id: UUID
    user_id: str
    username: str
    nickname: str
    avatar: str | None = None
    bio: str
    school_major: str
    campus: str
    contact_wx: str
    grade: int
    verified: bool
    email: str | None = None
    phone: str | None = None

    model_config = {"from_attributes": True}

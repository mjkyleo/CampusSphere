"""用户路由：/api/users/*。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.user.models import UserProfile
from app.modules.user.schemas import ProfileUpdateRequest, UserProfileOut
from app.modules.user.service import (
    get_profile,
    list_users,
    search_users,
    update_profile,
)

router = APIRouter(prefix="/api/users", tags=["user"])


def _build_profile_out(user: User, profile: UserProfile) -> UserProfileOut:
    """合并 User 与 UserProfile 字段构建输出（UserProfileOut 的 id 取用户 id）。"""
    return UserProfileOut.model_validate(
        {
            "id": user.id,
            "user_id": str(user.id),
            "username": user.username,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "bio": profile.bio,
            "school_major": profile.school_major,
            "campus": profile.campus,
            "contact_wx": profile.contact_wx,
            "grade": profile.grade,
            "verified": profile.verified,
            "email": user.email,
            "phone": user.phone,
        }
    )


@router.get("/me", response_model=ApiResponse[UserProfileOut])
async def get_me(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = await get_profile(db, user)
    return ApiResponse.ok(data=_build_profile_out(user, profile))


@router.patch("/me", response_model=ApiResponse[UserProfileOut])
async def update_me(
    data: ProfileUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = await update_profile(db, user, data)
    return ApiResponse.ok(data=_build_profile_out(user, profile))


@router.get("", response_model=ApiResponse[dict])
async def list_all(
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await list_users(db, q=q, page=page, page_size=page_size)
    return ApiResponse.ok(data=result)


@router.get("/search", response_model=ApiResponse[list])
async def search(
    q: str = Query(default="", min_length=1),
    limit: int = Query(default=20, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    hits = await search_users(db, q, limit=limit)
    return ApiResponse.ok(data=hits)

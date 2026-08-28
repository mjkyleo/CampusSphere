"""资源共享路由：/api/shares/*。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.share.schemas import ShareCreate, ShareOut
from app.modules.share.service import (
    create_share,
    get_share,
    increment_download,
    list_shares,
    presign_download,
)

router = APIRouter(prefix="/api/shares", tags=["share"])


@router.get("", response_model=ApiResponse[dict])
async def list_all(
    category: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return ApiResponse.ok(data=await list_shares(db, category=category, page=page, page_size=page_size))


@router.post("", response_model=ApiResponse[ShareOut])
async def create(data: ShareCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return ApiResponse.ok(data=ShareOut.model_validate(await create_share(db, user, data)))


@router.get("/{share_id}/download", response_model=ApiResponse[dict])
async def download(share_id: str, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    sr = await get_share(db, share_id)
    url = await presign_download(sr)
    await increment_download(db, sr)
    return ApiResponse.ok(data={"url": url})

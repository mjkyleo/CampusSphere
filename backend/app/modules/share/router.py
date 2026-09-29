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


# NOTE: 静态路径 /categories 必须先于 /{share_id} 声明，否则 "categories" 会被当作 share_id 匹配
@router.get("/categories", response_model=ApiResponse[dict])
async def categories(db: AsyncSession = Depends(get_db)):
    """公开读取学术资料分类（后台配置，含 school.yaml 兜底）。"""
    from app.modules.admin.service import get_share_categories

    return ApiResponse.ok(data={"categories": await get_share_categories(db)})


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


@router.post("/{share_id}/like", response_model=ApiResponse[dict])
async def like(share_id: str, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    """资源点赞（P2-22：此前前端是 localStorage mock，永不落库）。

    单条原子 UPDATE，并发点赞不丢计数；不做单用户去重（轻量社交信号，
    防刷由全局限流兜底）。
    """
    from sqlalchemy import func, select, update

    from app.core.exceptions import BizError, ErrorCode
    from app.modules.share.models import ShareResource

    result = await db.execute(
        update(ShareResource)
        .where(ShareResource.id == share_id)
        .values(likes=ShareResource.likes + 1)
    )
    if result.rowcount != 1:
        raise BizError(ErrorCode.NOT_FOUND, "资源不存在")
    await db.commit()
    likes = await db.scalar(
        select(func.coalesce(ShareResource.likes, 0)).where(ShareResource.id == share_id)
    )
    return ApiResponse.ok(data={"likes": int(likes or 0)})

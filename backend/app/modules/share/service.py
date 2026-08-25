"""资源共享业务逻辑。"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizError, ErrorCode
from app.core.storage import storage_client
from app.modules.auth.models import User
from app.modules.share.models import ShareResource
from app.modules.share.schemas import ShareCreate, ShareOut


async def list_shares(db: AsyncSession, category: str = "", page: int = 1, page_size: int = 20) -> dict:
    stmt = select(ShareResource)
    if category:
        stmt = stmt.where(ShareResource.category == category)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await db.scalars(stmt.order_by(ShareResource.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    return {
        "items": [ShareOut.model_validate(r).model_dump() for r in rows],
        "total": total or 0, "page": page, "page_size": page_size,
    }


async def create_share(db: AsyncSession, owner: User, data: ShareCreate) -> ShareResource:
    sr = ShareResource(owner_id=str(owner.id), **data.model_dump())
    db.add(sr)
    await db.commit()
    await db.refresh(sr)
    return sr


async def get_share(db: AsyncSession, share_id: str) -> ShareResource:
    sr = await db.get(ShareResource, share_id)
    if not sr:
        raise BizError(ErrorCode.NOT_FOUND, "资源不存在")
    return sr


async def presign_download(sr: ShareResource) -> str:
    return await storage_client.presigned_download_url(sr.file_key)


async def increment_download(db: AsyncSession, sr: ShareResource) -> None:
    sr.downloads += 1
    await db.commit()

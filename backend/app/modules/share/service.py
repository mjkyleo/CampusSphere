"""资源共享业务逻辑。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizError, ErrorCode
from app.core.storage import ensure_user_object_key, storage_client
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
    # 分类收敛到后台配置列表内（见 job.service.create_job 同名说明）
    from app.modules.admin.service import normalize_category

    # P1-2：schema 已把关形态，此处校验归属——file_key 必须签发给资源
    # owner 本人，防止把他人上传的私桶对象挂到自己的资源上下载。
    if data.file_key:
        try:
            ensure_user_object_key(data.file_key, str(owner.id))
        except ValueError as exc:
            raise BizError(ErrorCode.VALIDATION, "附件不属于当前用户，请重新上传") from exc

    payload = data.model_dump()
    payload["category"] = await normalize_category(db, "share", payload.get("category", ""))
    sr = ShareResource(owner_id=str(owner.id), **payload)
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
    # P2-6：`sr.downloads += 1` 是读-改-写，并发下载会互相覆盖丢失计数。
    # 改为单条原子 UPDATE（downloads = downloads + 1），由数据库保证累加。
    from sqlalchemy import update

    await db.execute(
        update(ShareResource)
        .where(ShareResource.id == sr.id)
        .values(downloads=ShareResource.downloads + 1)
    )
    await db.commit()
    await db.refresh(sr)

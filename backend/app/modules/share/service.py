"""资源共享业务逻辑。"""

from __future__ import annotations

import json
from collections.abc import Iterable

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.utils import escape_like
from app.core.exceptions import BizError, ErrorCode
from app.core.storage import ensure_user_object_key, storage_client
from app.modules.ai.service import check_content_safety
from app.modules.auth.models import User
from app.modules.share.models import ShareResource
from app.modules.share.schemas import ShareCreate, ShareOut


def _parse_tags(raw: object) -> list[str]:
    if isinstance(raw, list):
        values = raw
    elif isinstance(raw, str):
        try:
            values = json.loads(raw or "[]")
        except (TypeError, ValueError):
            values = []
    else:
        values = []
    return [str(tag) for tag in values if str(tag).strip()][:8]


async def _owner_nicknames(db: AsyncSession, owner_ids: Iterable[str]) -> dict[str, str]:
    ids = {str(owner_id) for owner_id in owner_ids if owner_id}
    if not ids:
        return {}
    rows = (
        await db.execute(
            select(User.id, User.nickname, User.username).where(User.id.in_(ids))
        )
    ).all()
    return {
        str(row[0]): (row[1] or row[2] or "")
        for row in rows
    }


def _to_out(sr: ShareResource, owner_nickname: str = "") -> ShareOut:
    payload = {
        "id": str(sr.id),
        "owner_id": str(sr.owner_id),
        "owner_nickname": owner_nickname,
        "title": sr.title,
        "description": sr.description or "",
        "file_key": sr.file_key or "",
        "file_url": sr.file_url or "",
        "category": sr.category,
        "downloads": int(sr.downloads or 0),
        "likes": int(sr.likes or 0),
        "tags": _parse_tags(getattr(sr, "tags", "[]")),
        "created_at": getattr(sr, "created_at", None),
        # 外链资源直接把用户提供的地址回给前端；平台自存文件才走签名下载。
        "download_url": sr.file_url or None,
    }
    return ShareOut.model_validate(payload)


async def list_shares(
    db: AsyncSession,
    category: str = "",
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    stmt = select(ShareResource)
    if category:
        stmt = stmt.where(ShareResource.category == category)
    if keyword:
        like = f"%{escape_like(keyword)}%"
        stmt = stmt.where(
            or_(
                ShareResource.title.ilike(like, escape="\\"),
                ShareResource.description.ilike(like, escape="\\"),
            )
        )
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await db.scalars(stmt.order_by(ShareResource.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    nicknames = await _owner_nicknames(db, [r.owner_id for r in rows])
    return {
        "items": [_to_out(r, nicknames.get(str(r.owner_id), "")).model_dump() for r in rows],
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
    payload["tags"] = json.dumps(payload.get("tags") or [], ensure_ascii=False)
    payload["category"] = await normalize_category(db, "share", payload.get("category", ""))

    # 内容预审：命中敏感词时拒绝发布（默认关闭，可在后台开启）
    moderation_text = f"{payload.get('title', '')}\n{payload.get('description', '')}".strip()
    moderation = await check_content_safety(db, moderation_text)
    if not moderation["safe"]:
        raise BizError(ErrorCode.FORBIDDEN, "发布内容涉嫌违规，请修改后重试")

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


async def get_share_out(db: AsyncSession, share_id: str) -> ShareOut:
    sr = await get_share(db, share_id)
    nicknames = await _owner_nicknames(db, [sr.owner_id])
    return _to_out(sr, nicknames.get(str(sr.owner_id), ""))


async def presign_download(sr: ShareResource) -> str:
    # 外链资源：平台不托管文件，直接返回用户提供的地址。
    if sr.file_url:
        return sr.file_url
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

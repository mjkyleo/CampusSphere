"""队友招募业务逻辑。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import MemberStatus, TeamStatus
from app.core.exceptions import BizError, ErrorCode
from app.modules.auth.models import User
from app.modules.teammate.models import Team, TeamMember
from app.modules.teammate.schemas import TeamCreate, TeamOut


async def list_teams(db: AsyncSession, page: int = 1, page_size: int = 20, category: str = "") -> dict:
    stmt = select(Team).where(Team.status == TeamStatus.RECRUITING.value)
    if category:
        stmt = stmt.where(Team.category == category)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await db.scalars(stmt.order_by(Team.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    items = []
    for t in rows:
        count = await db.scalar(
            select(func.count()).select_from(TeamMember).where(TeamMember.team_id == str(t.id))
        )
        out = TeamOut.model_validate(t).model_dump()
        out["member_count"] = count or 0
        items.append(out)
    return {"items": items, "total": total or 0, "page": page, "page_size": page_size}


async def create_team(db: AsyncSession, creator: User, data: TeamCreate) -> Team:
    # 分类收敛到后台配置列表内：前端传了已被运营下线的分类时，落到"其他"
    # 而不是把脏值写进库里（否则筛选页会出现一个点不动的空分类）。
    from app.modules.admin.service import normalize_category

    payload = data.model_dump()
    payload["category"] = await normalize_category(db, "teammate", payload.get("category", ""))
    team = Team(creator_id=str(creator.id), **payload, status=TeamStatus.RECRUITING.value)
    db.add(team)
    await db.flush()
    # 创建者自动成为活跃成员
    db.add(TeamMember(team_id=str(team.id), user_id=str(creator.id), status=MemberStatus.ACTIVE.value, role="队长"))
    await db.commit()
    await db.refresh(team)
    return team


async def get_team(db: AsyncSession, team_id: str) -> Team:
    team = await db.get(Team, team_id)
    if not team:
        raise BizError(ErrorCode.NOT_FOUND, "团队不存在")
    return team


async def join_team(db: AsyncSession, team: Team, user: User, role: str = "") -> TeamMember:
    if team.status != TeamStatus.RECRUITING.value:
        raise BizError(ErrorCode.CONFLICT, "团队已停止招募")
    existing = await db.scalar(
        select(TeamMember).where(TeamMember.team_id == str(team.id), TeamMember.user_id == str(user.id))
    )
    if existing:
        raise BizError(ErrorCode.CONFLICT, "已在团队中")
    member = TeamMember(
        team_id=str(team.id), user_id=str(user.id),
        role=role, status=MemberStatus.PENDING.value,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


async def list_members(db: AsyncSession, team_id: str) -> list:
    rows = (await db.scalars(
        select(TeamMember).where(TeamMember.team_id == team_id)
    )).all()
    return [m.model_dump() for m in rows]

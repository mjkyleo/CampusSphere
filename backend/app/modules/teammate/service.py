"""队友招募业务逻辑。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import MemberStatus, TeamStatus
from app.core.exceptions import BizError, ErrorCode
from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.teammate.models import Team, TeamMember
from app.modules.teammate.schemas import TeamCreate, TeamOut

_logger = get_logger("teammate.service")


async def list_teams(db: AsyncSession, page: int = 1, page_size: int = 20, category: str = "") -> dict:
    stmt = select(Team).where(Team.status == TeamStatus.RECRUITING.value)
    if category:
        stmt = stmt.where(Team.category == category)
    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await db.scalars(stmt.order_by(Team.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    # P2-18：一条 GROUP BY 取回本页全部队伍的成员计数，替代此前每行一次
    # COUNT 的 N+1（页大小 ≤100 时最多 100 次往返）。
    counts: dict[str, int] = {}
    if rows:
        count_rows = await db.execute(
            select(TeamMember.team_id, func.count())
            .where(TeamMember.team_id.in_([str(t.id) for t in rows]))
            .group_by(TeamMember.team_id)
        )
        counts = {team_id: n for team_id, n in count_rows.all()}
    items = []
    for t in rows:
        out = TeamOut.model_validate(t).model_dump()
        out["member_count"] = counts.get(str(t.id), 0)
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
    # P2-4：max_members 从未被执行——队伍人数无上限，FULL 状态永不出现。
    # 以现有成员数（含待审核）为上限判断，满员即拒绝并把队伍置为 FULL。
    member_count = await db.scalar(
        select(func.count()).select_from(TeamMember).where(TeamMember.team_id == str(team.id))
    )
    max_members = int(team.max_members or 0)
    if max_members > 0 and (member_count or 0) >= max_members:
        team.status = TeamStatus.FULL.value
        await db.commit()
        raise BizError(ErrorCode.CONFLICT, "队伍人数已满")
    member = TeamMember(
        team_id=str(team.id), user_id=str(user.id),
        role=role, status=MemberStatus.PENDING.value,
    )
    db.add(member)
    try:
        await db.commit()
    except IntegrityError as exc:
        # P2-4：并发双插由 uq_team_member 唯一索引兜底，转 409。
        await db.rollback()
        raise BizError(ErrorCode.CONFLICT, "已在团队中") from exc
    await db.refresh(member)
    # 满员后同步收敛队伍状态，让 FULL 真正出现
    if max_members > 0 and (member_count or 0) + 1 >= max_members:
        team.status = TeamStatus.FULL.value
        await db.commit()
    _logger.info("team_member_joined", team_id=str(team.id), user_id=str(user.id))
    return member


async def list_members(db: AsyncSession, team_id: str) -> list:
    rows = (await db.scalars(
        select(TeamMember).where(TeamMember.team_id == team_id)
    )).all()
    return [m.model_dump() for m in rows]


async def close_team(db: AsyncSession, team: Team, user: User) -> Team:
    """队长关闭招募：仅创建者可操作，状态 → DISBANDED（P2-22）。"""
    if str(team.creator_id) != str(user.id):
        raise BizError(ErrorCode.FORBIDDEN, "仅队长可关闭招募")
    team.status = TeamStatus.DISBANDED.value
    await db.commit()
    await db.refresh(team)
    _logger.info("team_closed", team_id=str(team.id), actor=str(user.id))
    return team

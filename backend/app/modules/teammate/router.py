"""队友招募路由：/api/teams/*。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.teammate.schemas import JoinRequest, TeamCreate, TeamMemberOut, TeamOut
from app.modules.teammate.service import (
    create_team,
    get_team,
    join_team,
    list_members,
    list_teams,
)

router = APIRouter(prefix="/api/teams", tags=["teammate"])


# NOTE: 静态路径 /categories 必须先于 /{team_id} 声明，否则 "categories" 会被当作 team_id 匹配
@router.get("/categories", response_model=ApiResponse[dict])
async def categories(db: AsyncSession = Depends(get_db)):
    """公开读取搭子组队分类（后台配置，含 school.yaml 兜底）。"""
    from app.modules.admin.service import get_teammate_categories

    return ApiResponse.ok(data={"categories": await get_teammate_categories(db)})


@router.get("", response_model=ApiResponse[dict])
async def list_all(
    category: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return ApiResponse.ok(
        data=await list_teams(db, page=page, page_size=page_size, category=category)
    )


@router.post("", response_model=ApiResponse[TeamOut])
async def create(data: TeamCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return ApiResponse.ok(data=TeamOut.model_validate(await create_team(db, user, data)))


@router.get("/{team_id}", response_model=ApiResponse[dict])
async def detail(team_id: str, db: AsyncSession = Depends(get_db)):
    team = await get_team(db, team_id)
    members = await list_members(db, str(team.id))
    return ApiResponse.ok(data={"team": TeamOut.model_validate(team).model_dump(), "members": members})


@router.post("/{team_id}/join", response_model=ApiResponse[TeamMemberOut])
async def join(team_id: str, data: JoinRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    team = await get_team(db, team_id)
    member = await join_team(db, team, user, data.role)
    return ApiResponse.ok(data=TeamMemberOut.model_validate(member))

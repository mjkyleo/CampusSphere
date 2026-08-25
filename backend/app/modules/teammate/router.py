"""队友招募路由：/api/teams/*。"""

from __future__ import annotations

import uuid

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


@router.get("", response_model=ApiResponse[dict])
async def list_all(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return ApiResponse.ok(data=await list_teams(db, page=page, page_size=page_size))


@router.post("", response_model=ApiResponse[TeamOut])
async def create(data: TeamCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return ApiResponse.ok(data=TeamOut.model_validate(await create_team(db, user, data)))


@router.get("/{team_id}", response_model=ApiResponse[dict])
async def detail(team_id: str, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    team = await get_team(db, team_id)
    members = await list_members(db, str(team.id))
    return ApiResponse.ok(data={"team": TeamOut.model_validate(team).model_dump(), "members": members})


@router.post("/{team_id}/join", response_model=ApiResponse[TeamMemberOut])
async def join(team_id: str, data: JoinRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    team = await get_team(db, team_id)
    member = await join_team(db, team, user, data.role)
    return ApiResponse.ok(data=TeamMemberOut.model_validate(member))

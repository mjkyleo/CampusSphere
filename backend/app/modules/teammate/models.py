"""队友招募 ORM 模型。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import MemberStatus, TeamStatus
from app.common.models import Base, PKMixin, TimestampMixin


class Team(Base, PKMixin, TimestampMixin):
    """招募团队。"""

    __tablename__ = "teams"

    creator_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    required_roles: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[int] = mapped_column(Integer, default=TeamStatus.RECRUITING.value, index=True)

    members: Mapped[list[TeamMember]] = relationship(
        back_populates="team", cascade="all, delete-orphan", lazy="selectin"
    )


class TeamMember(Base, PKMixin, TimestampMixin):
    """团队成员。"""

    __tablename__ = "team_members"

    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[int] = mapped_column(Integer, default=MemberStatus.PENDING.value, index=True)

    team: Mapped[Team] = relationship(back_populates="members")

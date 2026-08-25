"""管理后台 ORM 模型。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base, PKMixin, TimestampMixin


class AdminUser(Base, PKMixin, TimestampMixin):
    """后台管理员。"""

    __tablename__ = "admin_users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"), nullable=True)
    disabled: Mapped[bool] = mapped_column(default=False)

    role: Mapped["Role"] = relationship(back_populates="admins")


class Role(Base, PKMixin, TimestampMixin):
    """角色（RBAC）。"""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    permissions: Mapped[list] = mapped_column(JSON, default=list)  # 权限码列表

    admins: Mapped[list["AdminUser"]] = relationship(back_populates="role")


class Permission(Base, PKMixin, TimestampMixin):
    """权限点。"""

    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(64), unique=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255), default="")


class AppConfig(Base, PKMixin, TimestampMixin):
    """应用级 key-value 配置（JSON 值）。

    用于后台可动态修改的配置项：DB 值优先于 school.yaml 默认值，
    从而实现"默认配置走文件、运行时配置走后台"。
    """

    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)

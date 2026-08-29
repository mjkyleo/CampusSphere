"""公共 ORM 基础：DeclarativeBase、主键、时间戳、逻辑删除 Mixin。

所有业务模型必须继承 ``Base`` 并组合以下 Mixin，以保证：
- 统一 UUID 主键
- 统一 created_at / updated_at
- 统一软删除（deleted_at）
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 统一命名约定，保证 Alembic 迁移文件稳定可复现
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类。"""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class PKMixin:
    """UUID 主键 Mixin（以 36 位带连字符字符串存储，保证跨模块外键 JOIN 值完全一致）。"""

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )


class TimestampMixin:
    """创建/更新时间 Mixin（数据库 server_default，避免应用层时区漂移）。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """逻辑删除 Mixin，NULL 表示未删除。"""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )

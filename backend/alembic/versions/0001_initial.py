"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-08-25 00:00:00.000000

初始基线：依据 app.common.models.Base.metadata 一次性建表。
兼容 SQLite（开发/测试）与 PostgreSQL 16（生产）。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

from app.common.models import Base


# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

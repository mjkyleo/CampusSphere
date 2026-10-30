"""share_resources 补 likes 列

Revision ID: 0003_share_likes
Revises: 0002_campus_config
Create Date: 2026-10-25 00:00:00.000000

P2-22 把点赞数从前端 mock 落到 ORM（`ShareResource.likes`），但 0001 基线之后
没有对应迁移，已有数据库上 `/api/shares` 直接 500：
`sqlite3.OperationalError: no such column: share_resources.likes`。

幂等约定同 0002：0001 是快照式基线，全新库上该列已存在，必须先探测再加。
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Engine

revision: str = "0003_share_likes"
down_revision: Union[str, None] = "0002_campus_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns_of(bind: Engine, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if "likes" in _columns_of(bind, "share_resources"):
        return
    op.add_column(
        "share_resources",
        sa.Column("likes", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if "likes" not in _columns_of(bind, "share_resources"):
        return
    with op.batch_alter_table("share_resources") as batch_op:
        batch_op.drop_column("likes")

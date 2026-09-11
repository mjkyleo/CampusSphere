"""配置化扩展：食堂维度字段 + 分类配置化 + 并发加固索引

Revision ID: 0002_campus_config
Revises: 0001_initial
Create Date: 2026-09-04 00:00:00.000000

新增：
- canteens 表扩维（campus / zone / canteen_type / floor / description /
  features / popular_dishes / opening_hours / semester），对齐武大实际结构。
- teams 表新增 category / max_members / contact_info（分类改为后台配置驱动）。
- trade_sessions 表新增部分唯一索引 uq_trade_session_active_item
  （status IN (0,1) 唯一），与 item.service 的条件 UPDATE 并发抢占形成双保险。
- AppConfig 中新增 job/share/teammate/canteen 等配置行的键，由各自 service
  首读时惰性回退 school.yaml，无需在迁移中预填。

SQLite 与 PostgreSQL 兼容：features/popular_dishes 用 JSON/JSONB，
其余为可空带默认值的标量列，升级零停机。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_campus_config"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # ---------------- canteens 扩维 ----------------
    op.add_column("canteens", sa.Column("campus", sa.String(32), server_default="", nullable=False))
    op.add_column("canteens", sa.Column("zone", sa.String(32), server_default="", nullable=False))
    op.add_column("canteens", sa.Column("canteen_type", sa.String(32), server_default="", nullable=False))
    op.add_column("canteens", sa.Column("floor", sa.String(32), server_default="", nullable=False))
    op.add_column("canteens", sa.Column("description", sa.Text(), server_default="", nullable=False))
    # features / popular_dishes：PG 用 JSONB，SQLite 用 TEXT（存 JSON 串）
    if is_pg:
        op.add_column("canteens", sa.Column("features", postgresql.JSONB(), server_default="[]", nullable=False))
        op.add_column("canteens", sa.Column("popular_dishes", postgresql.JSONB(), server_default="[]", nullable=False))
    else:
        op.add_column("canteens", sa.Column("features", sa.Text(), server_default="[]", nullable=False))
        op.add_column("canteens", sa.Column("popular_dishes", sa.Text(), server_default="[]", nullable=False))
    op.add_column("canteens", sa.Column("opening_hours", sa.String(64), server_default="", nullable=False))
    op.add_column("canteens", sa.Column("semester", sa.String(32), server_default="", nullable=False))
    op.create_index("ix_canteens_campus", "canteens", ["campus"])
    op.create_index("ix_canteens_zone", "canteens", ["zone"])
    op.create_index("ix_canteens_canteen_type", "canteens", ["canteen_type"])
    op.create_index("ix_canteens_semester", "canteens", ["semester"])

    # ---------------- teams 分类化 ----------------
    op.add_column("teams", sa.Column("category", sa.String(32), server_default="其他", nullable=False))
    op.add_column("teams", sa.Column("max_members", sa.Integer(), server_default="3", nullable=False))
    op.add_column("teams", sa.Column("contact_info", sa.String(255), server_default="", nullable=False))
    op.create_index("ix_teams_category", "teams", ["category"])

    # ---------------- trade_sessions 并发唯一索引 ----------------
    # 部分唯一索引：同一 item 同时最多一个活跃（PENDING/IN_PROGRESS）会话。
    if is_pg:
        op.execute(
            "CREATE UNIQUE INDEX uq_trade_session_active_item "
            "ON trade_sessions (item_id) WHERE status IN (0, 1)"
        )
    else:
        op.execute(
            "CREATE UNIQUE INDEX uq_trade_session_active_item "
            "ON trade_sessions (item_id) WHERE status IN (0, 1)"
        )


def downgrade() -> None:
    op.drop_index("uq_trade_session_active_item", table_name="trade_sessions")
    op.drop_index("ix_teams_category", table_name="teams")
    op.drop_column("teams", "contact_info")
    op.drop_column("teams", "max_members")
    op.drop_column("teams", "category")
    op.drop_index("ix_canteens_semester", table_name="canteens")
    op.drop_index("ix_canteens_canteen_type", table_name="canteens")
    op.drop_index("ix_canteens_zone", table_name="canteens")
    op.drop_index("ix_canteens_campus", table_name="canteens")
    op.drop_column("canteens", "semester")
    op.drop_column("canteens", "opening_hours")
    op.drop_column("canteens", "popular_dishes")
    op.drop_column("canteens", "features")
    op.drop_column("canteens", "description")
    op.drop_column("canteens", "floor")
    op.drop_column("canteens", "canteen_type")
    op.drop_column("canteens", "zone")
    op.drop_column("canteens", "campus")

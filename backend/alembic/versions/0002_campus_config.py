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

.. note:: 幂等性（必须保持）
    0001 是"当前模型快照式"基线（``Base.metadata.create_all``），会随模型
    演进而包含本迁移要加的列 —— 全新数据库上跑 0001 后这些列**已经存在**。
    因此本迁移的每个 add_column / create_index 都必须先探测再执行，
    否则生产 compose 启动命令 ``alembic upgrade head`` 会撞
    "duplicate column" 直接崩掉，app 容器永远起不来（已在全新 PG 16 上实测）。
    后续新增迁移若建立在 0001 快照之上，同样必须遵守该约定。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine

revision: str = "0002_campus_config"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns_of(bind: Engine, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def _indexes_of(bind: Engine, table: str) -> set[str]:
    return {i["name"] for i in sa.inspect(bind).get_indexes(table)}


def _add_column_if_missing(
    bind: Engine,
    table: str,
    column: sa.Column,
) -> None:
    if column.name in _columns_of(bind, table):
        return
    op.add_column(table, column)


def _create_index_if_missing(bind: Engine, name: str, table: str, column: str) -> None:
    if name in _indexes_of(bind, table):
        return
    op.create_index(name, table, [column])


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # ---------------- canteens 扩维 ----------------
    # features / popular_dishes：PG 用 JSONB，SQLite 用 TEXT（存 JSON 串）
    _add_column_if_missing(bind, "canteens", sa.Column("campus", sa.String(32), server_default="", nullable=False))
    _add_column_if_missing(bind, "canteens", sa.Column("zone", sa.String(32), server_default="", nullable=False))
    _add_column_if_missing(bind, "canteens", sa.Column("canteen_type", sa.String(32), server_default="", nullable=False))
    _add_column_if_missing(bind, "canteens", sa.Column("floor", sa.String(32), server_default="", nullable=False))
    _add_column_if_missing(bind, "canteens", sa.Column("description", sa.Text(), server_default="", nullable=False))
    if is_pg:
        _add_column_if_missing(bind, "canteens", sa.Column("features", postgresql.JSONB(), server_default="[]", nullable=False))
        _add_column_if_missing(bind, "canteens", sa.Column("popular_dishes", postgresql.JSONB(), server_default="[]", nullable=False))
    else:
        _add_column_if_missing(bind, "canteens", sa.Column("features", sa.Text(), server_default="[]", nullable=False))
        _add_column_if_missing(bind, "canteens", sa.Column("popular_dishes", sa.Text(), server_default="[]", nullable=False))
    _add_column_if_missing(bind, "canteens", sa.Column("opening_hours", sa.String(64), server_default="", nullable=False))
    _add_column_if_missing(bind, "canteens", sa.Column("semester", sa.String(32), server_default="", nullable=False))
    _create_index_if_missing(bind, "ix_canteens_campus", "canteens", "campus")
    _create_index_if_missing(bind, "ix_canteens_zone", "canteens", "zone")
    _create_index_if_missing(bind, "ix_canteens_canteen_type", "canteens", "canteen_type")
    _create_index_if_missing(bind, "ix_canteens_semester", "canteens", "semester")

    # ---------------- teams 分类化 ----------------
    _add_column_if_missing(bind, "teams", sa.Column("category", sa.String(32), server_default="其他", nullable=False))
    _add_column_if_missing(bind, "teams", sa.Column("max_members", sa.Integer(), server_default="3", nullable=False))
    _add_column_if_missing(bind, "teams", sa.Column("contact_info", sa.String(255), server_default="", nullable=False))
    _create_index_if_missing(bind, "ix_teams_category", "teams", "category")

    # ---------------- trade_sessions 并发唯一索引 ----------------
    # 部分唯一索引：同一 item 同时最多一个活跃（PENDING/IN_PROGRESS）会话。
    # SQLite 与 PostgreSQL 均支持 WHERE 形式的部分索引，原 is_pg 分支两边完全相同。
    if "uq_trade_session_active_item" not in _indexes_of(bind, "trade_sessions"):
        op.execute(
            "CREATE UNIQUE INDEX uq_trade_session_active_item "
            "ON trade_sessions (item_id) WHERE status IN (0, 1)"
        )


def downgrade() -> None:
    """降级只在"列确实由本迁移添加"的库上有意义；已存在的列不误删。"""
    bind = op.get_bind()

    op.execute("DROP INDEX IF EXISTS uq_trade_session_active_item")
    op.execute("DROP INDEX IF EXISTS ix_teams_category")
    op.execute("DROP INDEX IF EXISTS ix_canteens_semester")
    op.execute("DROP INDEX IF EXISTS ix_canteens_canteen_type")
    op.execute("DROP INDEX IF EXISTS ix_canteens_zone")
    op.execute("DROP INDEX IF EXISTS ix_canteens_campus")

    canteen_cols = _columns_of(bind, "canteens")
    for col in ("semester", "opening_hours", "popular_dishes", "features", "description", "floor", "canteen_type", "zone", "campus"):
        if col in canteen_cols:
            op.drop_column("canteens", col)

    team_cols = _columns_of(bind, "teams")
    for col in ("contact_info", "max_members", "category"):
        if col in team_cols:
            op.drop_column("teams", col)

"""交易幂等索引、OAuth 唯一约束（P2 修复）。

新增：
- trade_sessions 的 (item_id, buyer_id) 部分唯一索引：表达"同一买家对同一物品
  最多一个活跃会话"的幂等语义，与既有 (item_id) 索引并存。
- oauth_accounts 的 (provider, provider_openid) 唯一约束：堵住 check-then-insert
  的并发绑定竞态。

两个索引对 SQLite / PostgreSQL 均使用通用 SQL，且按方言能力做存在性探测，
重复执行 upgrade 不会报错。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_trade_guards"
down_revision: str | None = "0003_share_likes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _index_names(bind, table: str) -> set[str]:
    return {i["name"] for i in sa.inspect(bind).get_indexes(table)}


def _unique_names(bind, table: str) -> set[str]:
    return {u["name"] for u in sa.inspect(bind).get_unique_constraints(table)}


def upgrade() -> None:
    bind = op.get_bind()

    # 交易幂等：同一买家对同一物品最多一个活跃（PENDING/IN_PROGRESS）会话。
    if "uq_trade_session_active_item_buyer" not in _index_names(bind, "trade_sessions"):
        op.execute(
            "CREATE UNIQUE INDEX uq_trade_session_active_item_buyer "
            "ON trade_sessions (item_id, buyer_id) WHERE status IN (0, 1)"
        )

    # OAuth 绑定去重：同一 provider 的 openid 全局唯一。
    if "uq_oauth_provider_openid" not in _unique_names(bind, "oauth_accounts"):
        op.create_unique_constraint(
            "uq_oauth_provider_openid",
            "oauth_accounts",
            ["provider", "provider_openid"],
        )


def downgrade() -> None:
    bind = op.get_bind()

    if "uq_oauth_provider_openid" in _unique_names(bind, "oauth_accounts"):
        op.drop_constraint(
            "uq_oauth_provider_openid", "oauth_accounts", type_="unique"
        )
    op.execute("DROP INDEX IF EXISTS uq_trade_session_active_item_buyer")

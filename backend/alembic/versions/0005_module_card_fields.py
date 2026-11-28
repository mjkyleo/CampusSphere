"""共享资源外链与兼职详情字段。

Revision ID: 0005_module_card_fields
Revises: 0004_trade_guards
Create Date: 2026-11-28 00:00:00.000000

共享资源多数是用户提供的外部链接而非平台自存文件；兼职卡片需要展示
结算周期、地点、联系方式和任职要求。两处均为新增列，按既有约定先探测再执行。
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_module_card_fields"
down_revision: str | None = "0004_trade_guards"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_names(bind, table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    share_columns = _column_names(bind, "share_resources")
    if "file_url" not in share_columns:
        op.add_column(
            "share_resources",
            sa.Column("file_url", sa.String(512), server_default="", nullable=False),
        )
    if "tags" not in share_columns:
        op.add_column(
            "share_resources",
            sa.Column("tags", sa.Text(), server_default="[]", nullable=False),
        )

    job_columns = _column_names(bind, "jobs")
    if "salary_type" not in job_columns:
        op.add_column(
            "jobs",
            sa.Column("salary_type", sa.Integer(), server_default="1", nullable=False),
        )
    if "location" not in job_columns:
        op.add_column(
            "jobs",
            sa.Column("location", sa.String(255), server_default="", nullable=False),
        )
    if "contact" not in job_columns:
        op.add_column(
            "jobs",
            sa.Column("contact", sa.String(255), server_default="", nullable=False),
        )
    if "requirements" not in job_columns:
        op.add_column(
            "jobs",
            sa.Column("requirements", sa.Text(), server_default="", nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()

    for table, columns in (
        ("share_resources", ("file_url", "tags")),
        ("jobs", ("salary_type", "location", "contact", "requirements")),
    ):
        existing = _column_names(bind, table)
        with op.batch_alter_table(table) as batch_op:
            for name in columns:
                if name in existing:
                    batch_op.drop_column(name)

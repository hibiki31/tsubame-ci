"""サーバ接続状態と構成情報を追加

Revision ID: 0002_server_monitoring
Revises: 0001_initial_schema
Create Date: 2026-07-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_server_monitoring"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "servers",
        sa.Column("connection_status", sa.String(length=20), server_default="unknown", nullable=False),
    )
    op.add_column("servers", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("servers", sa.Column("last_check_latency_ms", sa.Integer(), nullable=True))
    op.add_column("servers", sa.Column("last_check_error", sa.Text(), nullable=True))
    op.add_column("servers", sa.Column("hardware_info", sa.JSON(), nullable=True))
    op.add_column("servers", sa.Column("software_info", sa.JSON(), nullable=True))
    op.add_column("servers", sa.Column("inventory_collected_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        op.f("ix_servers_connection_status"),
        "servers",
        ["connection_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_servers_connection_status"), table_name="servers")
    op.drop_column("servers", "inventory_collected_at")
    op.drop_column("servers", "software_info")
    op.drop_column("servers", "hardware_info")
    op.drop_column("servers", "last_check_error")
    op.drop_column("servers", "last_check_latency_ms")
    op.drop_column("servers", "last_checked_at")
    op.drop_column("servers", "connection_status")

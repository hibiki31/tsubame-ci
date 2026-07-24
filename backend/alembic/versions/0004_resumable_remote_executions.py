"""SSH session から分離した実行の再追跡情報を追加する。

Revision ID: 0004_resumable_remote_executions
Revises: 0003_add_github_job_triggers
Create Date: 2026-07-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_resumable_remote_executions"
down_revision: Union[str, None] = "0003_add_github_job_triggers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_executions",
        sa.Column("server_id_snapshot", sa.Integer(), nullable=True),
    )
    op.add_column(
        "job_executions",
        sa.Column("script_snapshot", sa.Text(), nullable=True),
    )
    op.add_column(
        "job_executions",
        sa.Column("remote_execution_id", sa.String(32), nullable=True),
    )
    op.add_column(
        "job_executions",
        sa.Column("remote_process_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "job_executions",
        sa.Column(
            "stdout_offset",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "job_executions",
        sa.Column(
            "stderr_offset",
            sa.BigInteger(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "job_executions",
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "job_executions",
        sa.Column("tracking_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "job_executions",
        sa.Column(
            "cancel_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # 既存履歴にも参照元 Job の内容を補い、以後の Job 編集から切り離す。
    op.execute(
        """
        UPDATE job_executions AS execution
        SET
            server_id_snapshot = job.server_id,
            script_snapshot = job.script
        FROM jobs AS job
        WHERE execution.job_id = job.id
        """
    )
    op.alter_column(
        "job_executions",
        "server_id_snapshot",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "job_executions",
        "script_snapshot",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.create_index(
        "ix_job_executions_remote_execution_id",
        "job_executions",
        ["remote_execution_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_job_executions_remote_execution_id",
        table_name="job_executions",
    )
    op.drop_column("job_executions", "cancel_requested_at")
    op.drop_column("job_executions", "tracking_error")
    op.drop_column("job_executions", "last_synced_at")
    op.drop_column("job_executions", "stderr_offset")
    op.drop_column("job_executions", "stdout_offset")
    op.drop_column("job_executions", "remote_process_id")
    op.drop_column("job_executions", "remote_execution_id")
    op.drop_column("job_executions", "script_snapshot")
    op.drop_column("job_executions", "server_id_snapshot")

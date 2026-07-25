"""実行履歴を単発スクリプトにも対応させる。

Revision ID: 0006_ad_hoc_executions
Revises: 0005_shared_github_token
Create Date: 2026-07-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0006_ad_hoc_executions"
down_revision: Union[str, None] = "0005_shared_github_token"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    execution_kind = postgresql.ENUM(
        "JOB",
        "AD_HOC",
        name="executionkind",
    )
    execution_kind.create(bind, checkfirst=True)

    op.add_column(
        "job_executions",
        sa.Column(
            "execution_kind",
            postgresql.ENUM(
                "JOB",
                "AD_HOC",
                name="executionkind",
                create_type=False,
            ),
            server_default="JOB",
            nullable=False,
        ),
    )
    op.add_column(
        "job_executions",
        sa.Column("name_snapshot", sa.String(255), nullable=True),
    )
    op.add_column(
        "job_executions",
        sa.Column("server_name_snapshot", sa.String(255), nullable=True),
    )

    op.execute(
        """
        UPDATE job_executions AS execution
        SET
            name_snapshot = job.name,
            server_name_snapshot = server.name
        FROM jobs AS job
        JOIN servers AS server ON server.id = job.server_id
        WHERE execution.job_id = job.id
        """
    )
    op.alter_column(
        "job_executions",
        "name_snapshot",
        existing_type=sa.String(255),
        nullable=False,
    )
    op.alter_column(
        "job_executions",
        "server_name_snapshot",
        existing_type=sa.String(255),
        nullable=False,
    )

    op.drop_constraint(
        "job_executions_job_id_fkey",
        "job_executions",
        type_="foreignkey",
    )
    op.alter_column(
        "job_executions",
        "job_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.create_foreign_key(
        "job_executions_job_id_fkey",
        "job_executions",
        "jobs",
        ["job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_job_executions_execution_kind",
        "job_executions",
        ["execution_kind"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    incompatible_count = bind.scalar(
        sa.text(
            "SELECT COUNT(*) FROM job_executions "
            "WHERE execution_kind = 'AD_HOC' OR job_id IS NULL"
        )
    )
    if incompatible_count:
        raise RuntimeError(
            "単発実行またはJob削除後の履歴が存在するため"
            "0006をdowngradeできません"
        )

    op.drop_index(
        "ix_job_executions_execution_kind",
        table_name="job_executions",
    )
    op.drop_constraint(
        "job_executions_job_id_fkey",
        "job_executions",
        type_="foreignkey",
    )
    op.alter_column(
        "job_executions",
        "job_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "job_executions_job_id_fkey",
        "job_executions",
        "jobs",
        ["job_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_column("job_executions", "server_name_snapshot")
    op.drop_column("job_executions", "name_snapshot")
    op.drop_column("job_executions", "execution_kind")
    postgresql.ENUM(name="executionkind").drop(bind, checkfirst=True)

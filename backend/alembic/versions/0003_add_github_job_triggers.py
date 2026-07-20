"""ジョブへ GitHub branch ポーリングトリガーを追加する。

Revision ID: 0003_add_github_job_triggers
Revises: 0002_server_monitoring
Create Date: 2026-07-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0003_add_github_job_triggers"
down_revision: Union[str, None] = "0002_server_monitoring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    job_trigger_type = postgresql.ENUM(
        "MANUAL",
        "GITHUB_POLL",
        name="jobtriggertype",
    )
    execution_trigger_source = postgresql.ENUM(
        "MANUAL",
        "GITHUB_POLL",
        name="executiontriggersource",
    )
    job_trigger_type.create(bind, checkfirst=True)
    execution_trigger_source.create(bind, checkfirst=True)

    op.add_column(
        "jobs",
        sa.Column(
            "trigger_type",
            postgresql.ENUM(
                "MANUAL",
                "GITHUB_POLL",
                name="jobtriggertype",
                create_type=False,
            ),
            server_default="MANUAL",
            nullable=False,
        ),
    )
    op.add_column("jobs", sa.Column("github_repository", sa.String(255), nullable=True))
    op.add_column("jobs", sa.Column("github_branch", sa.String(255), nullable=True))
    op.add_column("jobs", sa.Column("github_token_encrypted", sa.String(2000), nullable=True))
    op.add_column("jobs", sa.Column("github_last_commit_sha", sa.String(40), nullable=True))
    op.add_column("jobs", sa.Column("github_etag", sa.String(255), nullable=True))
    op.add_column("jobs", sa.Column("github_last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("github_last_error", sa.Text(), nullable=True))
    op.create_index("ix_jobs_trigger_type", "jobs", ["trigger_type"], unique=False)

    op.add_column(
        "job_executions",
        sa.Column(
            "trigger_source",
            postgresql.ENUM(
                "MANUAL",
                "GITHUB_POLL",
                name="executiontriggersource",
                create_type=False,
            ),
            server_default="MANUAL",
            nullable=False,
        ),
    )
    op.add_column(
        "job_executions",
        sa.Column("trigger_commit_sha", sa.String(40), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job_executions", "trigger_commit_sha")
    op.drop_column("job_executions", "trigger_source")
    op.drop_index("ix_jobs_trigger_type", table_name="jobs")
    op.drop_column("jobs", "github_last_error")
    op.drop_column("jobs", "github_last_checked_at")
    op.drop_column("jobs", "github_etag")
    op.drop_column("jobs", "github_last_commit_sha")
    op.drop_column("jobs", "github_token_encrypted")
    op.drop_column("jobs", "github_branch")
    op.drop_column("jobs", "github_repository")
    op.drop_column("jobs", "trigger_type")

    bind = op.get_bind()
    postgresql.ENUM(name="executiontriggersource").drop(bind, checkfirst=True)
    postgresql.ENUM(name="jobtriggertype").drop(bind, checkfirst=True)

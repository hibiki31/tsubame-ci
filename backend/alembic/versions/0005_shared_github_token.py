"""ジョブ間で共有する GitHub PAT と認証元を追加する。

Revision ID: 0005_shared_github_token
Revises: 0004_resumable_remote_executions
Create Date: 2026-07-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0005_shared_github_token"
down_revision: Union[str, None] = "0004_resumable_remote_executions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    github_token_source = postgresql.ENUM(
        "NONE",
        "SHARED",
        "JOB",
        name="githubtokensource",
    )
    github_token_source.create(bind, checkfirst=True)

    job_columns = {
        column["name"] for column in inspector.get_columns("jobs")
    }
    if "github_token_source" not in job_columns:
        op.add_column(
            "jobs",
            sa.Column(
                "github_token_source",
                postgresql.ENUM(
                    "NONE",
                    "SHARED",
                    "JOB",
                    name="githubtokensource",
                    create_type=False,
                ),
                server_default="NONE",
                nullable=False,
            ),
        )

    # 既存のジョブ固有 PAT は、そのままジョブ固有認証として引き継ぐ。
    op.execute(
        """
        UPDATE jobs
        SET github_token_source = 'JOB'
        WHERE
            github_token_encrypted IS NOT NULL
            AND github_token_source = 'NONE'
        """
    )

    if "github_tokens" not in inspector.get_table_names():
        op.create_table(
            "github_tokens",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("token_encrypted", sa.String(2000), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint(
                "id = 1",
                name="ck_github_tokens_singleton",
            ),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("github_tokens")
    op.drop_column("jobs", "github_token_source")

    bind = op.get_bind()
    postgresql.ENUM(name="githubtokensource").drop(bind, checkfirst=True)

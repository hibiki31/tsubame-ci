"""GitHub トリガー導入前の既存 schema を baseline 化する。

Revision ID: 0001_existing_schema_baseline
Revises:
Create Date: 2026-07-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_existing_schema_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column(
            "auth_method",
            sa.Enum("PASSWORD", "KEY", name="authmethod"),
            nullable=False,
        ),
        sa.Column("password_encrypted", sa.String(length=500), nullable=True),
        sa.Column("private_key_encrypted", sa.String(length=5000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_servers_id", "servers", ["id"], unique=False)

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("script", sa.Text(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_id", "jobs", ["id"], unique=False)
    op.create_index("ix_jobs_name", "jobs", ["name"], unique=False)
    op.create_index("ix_jobs_server_id", "jobs", ["server_id"], unique=False)

    op.create_table(
        "job_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "RUNNING",
                "SUCCESS",
                "FAILED",
                "TIMEOUT",
                "CANCELLED",
                name="executionstatus",
            ),
            nullable=False,
        ),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_executions_id", "job_executions", ["id"], unique=False)
    op.create_index("ix_job_executions_job_id", "job_executions", ["job_id"], unique=False)
    op.create_index("ix_job_executions_status", "job_executions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_job_executions_status", table_name="job_executions")
    op.drop_index("ix_job_executions_job_id", table_name="job_executions")
    op.drop_index("ix_job_executions_id", table_name="job_executions")
    op.drop_table("job_executions")
    op.drop_index("ix_jobs_server_id", table_name="jobs")
    op.drop_index("ix_jobs_name", table_name="jobs")
    op.drop_index("ix_jobs_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_servers_id", table_name="servers")
    op.drop_table("servers")
    sa.Enum(name="executionstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="authmethod").drop(op.get_bind(), checkfirst=True)

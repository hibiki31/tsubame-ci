"""既存 MVP database を安全に baseline 化して Alembic を適用する。"""

import asyncio
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.database import engine


BASELINE_REVISION = "0001_existing_schema_baseline"
CORE_TABLES = {"servers", "jobs", "job_executions"}
GITHUB_JOB_COLUMNS = {
    "trigger_type",
    "github_repository",
    "github_branch",
    "github_token_encrypted",
    "github_last_commit_sha",
    "github_etag",
    "github_last_checked_at",
    "github_last_error",
}
TRIGGER_EXECUTION_COLUMNS = {"trigger_source", "trigger_commit_sha"}


async def detect_schema_state() -> str:
    async with engine.connect() as connection:
        def inspect_schema(sync_connection) -> str:
            inspector = inspect(sync_connection)
            tables = set(inspector.get_table_names())
            if "alembic_version" in tables:
                return "managed"
            present_core_tables = tables & CORE_TABLES
            if not present_core_tables:
                return "empty"
            if present_core_tables != CORE_TABLES:
                missing = ", ".join(sorted(CORE_TABLES - present_core_tables))
                raise RuntimeError(
                    f"既存databaseの必須tableが不足しています: {missing}"
                )

            job_columns = {
                column["name"] for column in inspector.get_columns("jobs")
            }
            execution_columns = {
                column["name"] for column in inspector.get_columns("job_executions")
            }
            has_job_trigger_columns = GITHUB_JOB_COLUMNS <= job_columns
            has_execution_trigger_columns = (
                TRIGGER_EXECUTION_COLUMNS <= execution_columns
            )
            if has_job_trigger_columns and has_execution_trigger_columns:
                return "head_without_version"
            if not (job_columns & GITHUB_JOB_COLUMNS) and not (
                execution_columns & TRIGGER_EXECUTION_COLUMNS
            ):
                return "legacy"
            raise RuntimeError(
                "GitHubトリガーのcolumnが一部だけ存在します。"
                "database schemaを確認してからmigrationを再実行してください"
            )

        state = await connection.run_sync(inspect_schema)
    await engine.dispose()
    return state


def main() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    state = asyncio.run(detect_schema_state())

    if state == "legacy":
        command.stamp(config, BASELINE_REVISION)
    elif state == "head_without_version":
        command.stamp(config, "head")
        return

    command.upgrade(config, "head")


if __name__ == "__main__":
    main()

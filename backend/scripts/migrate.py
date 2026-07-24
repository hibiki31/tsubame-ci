"""既存 MVP database を判定し、単一 Alembic revision chain へ移行する。"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.core.database import engine


INITIAL_REVISION = "0001_initial_schema"
SERVER_REVISION = "0002_server_monitoring"
GITHUB_REVISION = "0003_add_github_job_triggers"
HEAD_REVISION = "0004_resumable_remote_executions"
LEGACY_TRIGGER_BASELINE = "0001_existing_schema_baseline"
LEGACY_TRIGGER_REVISION = "0002_add_github_job_triggers"
CORE_TABLES = {"servers", "jobs", "job_executions"}
SERVER_MONITOR_COLUMNS = {
    "connection_status",
    "last_checked_at",
    "last_check_latency_ms",
    "last_check_error",
    "hardware_info",
    "software_info",
    "inventory_collected_at",
}
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
RESUMABLE_EXECUTION_COLUMNS = {
    "server_id_snapshot",
    "script_snapshot",
    "remote_execution_id",
    "remote_process_id",
    "stdout_offset",
    "stderr_offset",
    "last_synced_at",
    "tracking_error",
    "cancel_requested_at",
}


@dataclass(frozen=True)
class SchemaState:
    empty: bool
    revision: str | None
    has_server_monitoring: bool
    has_github_triggers: bool
    has_resumable_executions: bool


async def detect_schema_state() -> SchemaState:
    async with engine.connect() as connection:
        def inspect_schema(sync_connection) -> tuple[bool, bool, bool, bool]:
            inspector = inspect(sync_connection)
            tables = set(inspector.get_table_names())
            present_core_tables = tables & CORE_TABLES
            if not present_core_tables:
                return True, False, False, False
            if present_core_tables != CORE_TABLES:
                missing = ", ".join(sorted(CORE_TABLES - present_core_tables))
                raise RuntimeError(
                    f"既存databaseの必須tableが不足しています: {missing}"
                )

            server_columns = {
                column["name"] for column in inspector.get_columns("servers")
            }
            job_columns = {
                column["name"] for column in inspector.get_columns("jobs")
            }
            execution_columns = {
                column["name"] for column in inspector.get_columns("job_executions")
            }
            server_present = server_columns & SERVER_MONITOR_COLUMNS
            trigger_job_present = job_columns & GITHUB_JOB_COLUMNS
            trigger_execution_present = (
                execution_columns & TRIGGER_EXECUTION_COLUMNS
            )
            resumable_execution_present = (
                execution_columns & RESUMABLE_EXECUTION_COLUMNS
            )
            if server_present and server_present != SERVER_MONITOR_COLUMNS:
                raise RuntimeError("サーバ監視columnが一部だけ存在します")
            if (
                trigger_job_present
                and trigger_job_present != GITHUB_JOB_COLUMNS
            ) or (
                trigger_execution_present
                and trigger_execution_present != TRIGGER_EXECUTION_COLUMNS
            ) or bool(trigger_job_present) != bool(trigger_execution_present):
                raise RuntimeError("GitHubトリガーcolumnが一部だけ存在します")
            if (
                resumable_execution_present
                and resumable_execution_present != RESUMABLE_EXECUTION_COLUMNS
            ):
                raise RuntimeError("再追跡実行columnが一部だけ存在します")
            if resumable_execution_present and (
                trigger_job_present != GITHUB_JOB_COLUMNS
            ):
                raise RuntimeError(
                    "再追跡実行columnにはGitHubトリガーcolumnが必要です"
                )
            return (
                False,
                server_present == SERVER_MONITOR_COLUMNS,
                trigger_job_present == GITHUB_JOB_COLUMNS,
                resumable_execution_present == RESUMABLE_EXECUTION_COLUMNS,
            )

        (
            empty,
            has_server_monitoring,
            has_github_triggers,
            has_resumable_executions,
        ) = (
            await connection.run_sync(inspect_schema)
        )
        revision = None
        if not empty:
            inspector_tables = await connection.run_sync(
                lambda sync_connection: set(inspect(sync_connection).get_table_names())
            )
            if "alembic_version" in inspector_tables:
                revisions = list(
                    (
                        await connection.execute(
                            text("SELECT version_num FROM alembic_version")
                        )
                    ).scalars()
                )
                if len(revisions) > 1:
                    raise RuntimeError("複数のAlembic headが登録されています")
                revision = revisions[0] if revisions else None

    await engine.dispose()
    return SchemaState(
        empty=empty,
        revision=revision,
        has_server_monitoring=has_server_monitoring,
        has_github_triggers=has_github_triggers,
        has_resumable_executions=has_resumable_executions,
    )


def stamp(config: Config, revision: str) -> None:
    command.stamp(config, revision, purge=True)


def upgrade_legacy_schema(config: Config, state: SchemaState) -> None:
    """Alembic 導入前 schema を、存在する column に合わせて baseline 化する。"""

    if state.has_resumable_executions:
        stamp(config, HEAD_REVISION)
    elif state.has_server_monitoring and state.has_github_triggers:
        stamp(config, GITHUB_REVISION)
        command.upgrade(config, "head")
    elif state.has_server_monitoring:
        stamp(config, SERVER_REVISION)
        command.upgrade(config, "head")
    elif state.has_github_triggers:
        # 旧 trigger branch 適用済み DB には server migration だけを適用する。
        stamp(config, INITIAL_REVISION)
        command.upgrade(config, SERVER_REVISION)
        stamp(config, GITHUB_REVISION)
        command.upgrade(config, "head")
    else:
        stamp(config, INITIAL_REVISION)
        command.upgrade(config, "head")


def main() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    state = asyncio.run(detect_schema_state())

    if state.empty:
        command.upgrade(config, "head")
        return
    if state.revision in {
        INITIAL_REVISION,
        SERVER_REVISION,
        GITHUB_REVISION,
        HEAD_REVISION,
    }:
        command.upgrade(config, "head")
        return
    if state.revision in {
        None,
        LEGACY_TRIGGER_BASELINE,
        LEGACY_TRIGGER_REVISION,
    }:
        upgrade_legacy_schema(config, state)
        return
    raise RuntimeError(f"未対応のAlembic revisionです: {state.revision}")


if __name__ == "__main__":
    main()

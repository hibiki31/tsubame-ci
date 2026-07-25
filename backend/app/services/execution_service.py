"""ジョブ実行の投入、永続追跡、状態遷移、履歴取得を管理する。"""

import asyncio
from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.execution import (
    ExecutionKind,
    ExecutionStatus,
    ExecutionTriggerSource,
    JobExecution,
)
from app.services.job_service import JobService
from app.services.remote_execution_service import (
    RemoteExecutionError,
    RemoteExecutionSnapshot,
    RemoteExecutionState,
    remote_execution_service,
)
from app.services.server_service import ServerService
from app.services.ssh_service import SSHConnectionError


class ExecutionNotFoundError(Exception):
    """実行履歴が見つからない。"""


class ExecutionService:
    """DB とリモート spool を同期するジョブ実行サービス。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_service = JobService(db)
        self.server_service = ServerService(db)
        self.remote_execution = remote_execution_service
        self.poll_interval = settings.execution_poll_interval_seconds
        self.reconnect_max_interval = (
            settings.execution_reconnect_max_interval_seconds
        )
        self.execution_timeout = settings.execution_timeout_seconds

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        include_job: bool = False,
    ) -> List[JobExecution]:
        query = (
            select(JobExecution)
            .order_by(desc(JobExecution.created_at))
            .limit(limit)
            .offset(offset)
        )
        if include_job:
            query = query.options(selectinload(JobExecution.job))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(
        self,
        execution_id: int,
        include_job: bool = False,
    ) -> JobExecution:
        query = select(JobExecution).where(JobExecution.id == execution_id)
        if include_job:
            query = query.options(selectinload(JobExecution.job))
        result = await self.db.execute(query)
        execution = result.scalar_one_or_none()
        if not execution:
            raise ExecutionNotFoundError(f"実行ID {execution_id} が見つかりません")
        return execution

    async def get_by_job_id(
        self,
        job_id: int,
        limit: int = 50,
        include_job: bool = False,
    ) -> List[JobExecution]:
        query = (
            select(JobExecution)
            .where(JobExecution.job_id == job_id)
            .order_by(desc(JobExecution.created_at))
            .limit(limit)
        )
        if include_job:
            query = query.options(selectinload(JobExecution.job))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_pending(
        self,
        job_id: int,
        trigger_source: ExecutionTriggerSource = ExecutionTriggerSource.MANUAL,
        trigger_commit_sha: str | None = None,
    ) -> JobExecution:
        """実行時の server/script とともに実行待ちレコードを永続化する。"""

        job = await self.job_service.get_by_id(job_id)
        server = await self.server_service.get_by_id(job.server_id)
        return await self._create_pending(
            job_id=job_id,
            execution_kind=ExecutionKind.JOB,
            name=job.name,
            server_id=job.server_id,
            server_name=server.name,
            script=job.script,
            trigger_source=trigger_source,
            trigger_commit_sha=trigger_commit_sha,
        )

    async def create_ad_hoc_pending(
        self,
        *,
        name: str,
        server_id: int,
        script: str,
    ) -> JobExecution:
        """単発スクリプトの実行待ちレコードを永続化する。"""

        server = await self.server_service.get_by_id(server_id)
        return await self._create_pending(
            job_id=None,
            execution_kind=ExecutionKind.AD_HOC,
            name=name,
            server_id=server_id,
            server_name=server.name,
            script=script,
            trigger_source=ExecutionTriggerSource.MANUAL,
        )

    async def _create_pending(
        self,
        *,
        job_id: int | None,
        execution_kind: ExecutionKind,
        name: str,
        server_id: int,
        server_name: str,
        script: str,
        trigger_source: ExecutionTriggerSource,
        trigger_commit_sha: str | None = None,
    ) -> JobExecution:
        """実行元に依存しない実行スナップショットを作成する。"""

        execution = JobExecution(
            job_id=job_id,
            execution_kind=execution_kind,
            name_snapshot=name,
            status=ExecutionStatus.PENDING,
            trigger_source=trigger_source,
            trigger_commit_sha=trigger_commit_sha,
            server_id_snapshot=server_id,
            server_name_snapshot=server_name,
            script_snapshot=script,
        )
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def execute_pending(self, execution_id: int) -> JobExecution:
        """PENDING を claim するか、RUNNING のリモート実行を再追跡する。"""

        execution = await self._claim_or_resume(execution_id)
        if execution.status != ExecutionStatus.RUNNING:
            return execution

        await self._track_remote(execution_id)
        return await self._reload_execution(execution_id)

    async def cancel_execution(self, execution_id: int) -> JobExecution:
        """キャンセル要求を永続化する。リモート停止は tracker が再試行する。"""

        result = await self.db.execute(
            select(JobExecution)
            .where(JobExecution.id == execution_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            raise ExecutionNotFoundError(f"実行ID {execution_id} が見つかりません")

        if execution.status == ExecutionStatus.PENDING:
            execution.status = ExecutionStatus.CANCELLED
            execution.finished_at = datetime.now(timezone.utc)
            execution.error_message = "ユーザーによってキャンセルされました"
        elif execution.status == ExecutionStatus.RUNNING:
            execution.cancel_requested_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def _claim_or_resume(self, execution_id: int) -> JobExecution:
        result = await self.db.execute(
            select(JobExecution)
            .where(JobExecution.id == execution_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            raise ExecutionNotFoundError(f"実行ID {execution_id} が見つかりません")

        if execution.status == ExecutionStatus.PENDING:
            if not execution.script_snapshot or not execution.server_id_snapshot:
                if execution.job_id is None:
                    execution.status = ExecutionStatus.FAILED
                    execution.finished_at = datetime.now(timezone.utc)
                    execution.error_message = (
                        "単発実行の再追跡に必要なスナップショットがありません"
                    )
                    await self.db.commit()
                    return execution
                job = await self.job_service.get_by_id(execution.job_id)
                execution.script_snapshot = job.script
                execution.server_id_snapshot = job.server_id
            execution.remote_execution_id = uuid4().hex
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.now(timezone.utc)
            execution.tracking_error = None
            await self.db.commit()
            return execution

        if (
            execution.status == ExecutionStatus.RUNNING
            and not execution.remote_execution_id
        ):
            # 旧方式で Backend process とともに失われた実行を放置しない。
            execution.status = ExecutionStatus.FAILED
            execution.finished_at = datetime.now(timezone.utc)
            execution.error_message = (
                "Backend再起動前の実行で再追跡情報がないため、"
                "リモート状態を復元できませんでした"
            )

        await self.db.commit()
        return execution

    async def _track_remote(self, execution_id: int) -> None:
        reconnect_delay = self.poll_interval
        needs_start = True
        dead_observations = 0

        while True:
            execution = await self._reload_execution(execution_id)
            if execution.status != ExecutionStatus.RUNNING:
                return

            server = await self.server_service.get_by_id(
                execution.server_id_snapshot
            )
            # 読み取り transaction を SSH 待機中まで保持しない。
            await self.db.commit()
            timed_out = self._has_timed_out(execution)

            try:
                if needs_start:
                    await self.remote_execution.ensure_started(
                        server,
                        execution.remote_execution_id,
                        execution.script_snapshot,
                    )
                    needs_start = False

                if execution.cancel_requested_at is not None or timed_out:
                    await self.remote_execution.request_cancel(
                        server,
                        execution.remote_execution_id,
                    )

                snapshot = await self.remote_execution.snapshot(
                    server,
                    execution.remote_execution_id,
                    execution.stdout_offset,
                    execution.stderr_offset,
                )
            except SSHConnectionError as error:
                await self._record_tracking_error(execution_id, str(error))
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(
                    self.reconnect_max_interval,
                    max(self.poll_interval, reconnect_delay * 2),
                )
                continue
            except RemoteExecutionError as error:
                await self._mark_failed(execution_id, str(error))
                return

            reconnect_delay = self.poll_interval
            terminal = await self._apply_snapshot(
                execution_id,
                execution.stdout_offset,
                execution.stderr_offset,
                snapshot,
                timed_out=timed_out,
            )
            if terminal:
                return

            if snapshot.state in {
                RemoteExecutionState.MISSING,
                RemoteExecutionState.STARTING,
            }:
                needs_start = True

            if snapshot.state == RemoteExecutionState.RUNNING and not snapshot.alive:
                dead_observations += 1
                if dead_observations >= 2:
                    await self._mark_failed(
                        execution_id,
                        "リモート実行プロセスが終了状態を記録せず停止しました",
                    )
                    return
            else:
                dead_observations = 0

            # terminal log が1 chunkを超える場合は、待たずに最後まで回収する。
            if snapshot.terminal and not snapshot.logs_complete:
                await asyncio.sleep(0)
            else:
                await asyncio.sleep(self.poll_interval)

    async def _reload_execution(self, execution_id: int) -> JobExecution:
        result = await self.db.execute(
            select(JobExecution)
            .where(JobExecution.id == execution_id)
            .execution_options(populate_existing=True)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            raise ExecutionNotFoundError(f"実行ID {execution_id} が見つかりません")
        await self.db.commit()
        return execution

    async def _apply_snapshot(
        self,
        execution_id: int,
        expected_stdout_offset: int,
        expected_stderr_offset: int,
        snapshot: RemoteExecutionSnapshot,
        *,
        timed_out: bool,
    ) -> bool:
        result = await self.db.execute(
            select(JobExecution)
            .where(JobExecution.id == execution_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        execution = result.scalar_one_or_none()
        if not execution:
            raise ExecutionNotFoundError(f"実行ID {execution_id} が見つかりません")
        if execution.status != ExecutionStatus.RUNNING:
            await self.db.commit()
            return True

        execution.remote_process_id = (
            snapshot.process_id or execution.remote_process_id
        )
        execution.last_synced_at = datetime.now(timezone.utc)
        execution.tracking_error = None

        offsets_match = (
            execution.stdout_offset == expected_stdout_offset
            and execution.stderr_offset == expected_stderr_offset
        )
        if offsets_match:
            if snapshot.stdout.text:
                execution.stdout = (execution.stdout or "") + snapshot.stdout.text
            if snapshot.stderr.text:
                execution.stderr = (execution.stderr or "") + snapshot.stderr.text
            execution.stdout_offset = snapshot.stdout.next_offset
            execution.stderr_offset = snapshot.stderr.next_offset

        can_finish = snapshot.logs_complete and offsets_match
        if snapshot.state == RemoteExecutionState.FINISHED and can_finish:
            execution.exit_code = snapshot.exit_code
            if snapshot.exit_code is None:
                execution.status = ExecutionStatus.FAILED
                execution.error_message = "リモート終了コードを取得できませんでした"
            elif snapshot.exit_code == 0:
                execution.status = ExecutionStatus.SUCCESS
                execution.error_message = None
            else:
                execution.status = ExecutionStatus.FAILED
                execution.error_message = (
                    f"スクリプトが終了コード {snapshot.exit_code} で終了しました"
                )
            execution.finished_at = snapshot.finished_at or datetime.now(timezone.utc)
        elif snapshot.state == RemoteExecutionState.CANCELLED and can_finish:
            execution.exit_code = snapshot.exit_code
            execution.finished_at = snapshot.finished_at or datetime.now(timezone.utc)
            if timed_out and execution.cancel_requested_at is None:
                execution.status = ExecutionStatus.TIMEOUT
                execution.error_message = (
                    f"スクリプト実行がタイムアウトしました（{self.execution_timeout}秒）"
                )
            else:
                execution.status = ExecutionStatus.CANCELLED
                execution.error_message = "ユーザーによってキャンセルされました"

        terminal = execution.status != ExecutionStatus.RUNNING
        await self.db.commit()
        return terminal

    async def _record_tracking_error(
        self,
        execution_id: int,
        message: str,
    ) -> None:
        result = await self.db.execute(
            select(JobExecution)
            .where(JobExecution.id == execution_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        execution = result.scalar_one_or_none()
        if execution and execution.status == ExecutionStatus.RUNNING:
            execution.tracking_error = f"SSH通信を再試行しています: {message}"
        await self.db.commit()

    async def _mark_failed(self, execution_id: int, message: str) -> None:
        result = await self.db.execute(
            select(JobExecution)
            .where(JobExecution.id == execution_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        execution = result.scalar_one_or_none()
        if execution and execution.status == ExecutionStatus.RUNNING:
            execution.status = ExecutionStatus.FAILED
            execution.finished_at = datetime.now(timezone.utc)
            execution.error_message = message
        await self.db.commit()

    def _has_timed_out(self, execution: JobExecution) -> bool:
        if self.execution_timeout <= 0 or execution.started_at is None:
            return False
        started_at = execution.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
        return elapsed >= self.execution_timeout

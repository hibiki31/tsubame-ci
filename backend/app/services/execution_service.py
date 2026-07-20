"""ジョブ実行の投入、状態遷移、履歴取得を管理する。"""

import asyncio
from datetime import datetime, timezone
from typing import List

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.execution import (
    ExecutionStatus,
    ExecutionTriggerSource,
    JobExecution,
)
from app.services.job_service import JobService
from app.services.ssh_service import SSHConnectionError, SSHExecutionError, ssh_service


class ExecutionNotFoundError(Exception):
    """実行履歴が見つからない。"""


class ExecutionService:
    """ジョブ実行サービス。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.job_service = JobService(db)

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

    async def get_by_job_id(self, job_id: int, limit: int = 50) -> List[JobExecution]:
        result = await self.db.execute(
            select(JobExecution)
            .where(JobExecution.job_id == job_id)
            .order_by(desc(JobExecution.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_pending(
        self,
        job_id: int,
        trigger_source: ExecutionTriggerSource = ExecutionTriggerSource.MANUAL,
        trigger_commit_sha: str | None = None,
    ) -> JobExecution:
        """実行待ちレコードを永続化する。"""

        await self.job_service.get_by_id(job_id)
        execution = JobExecution(
            job_id=job_id,
            status=ExecutionStatus.PENDING,
            trigger_source=trigger_source,
            trigger_commit_sha=trigger_commit_sha,
        )
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def create_and_execute(
        self,
        job_id: int,
        trigger_source: ExecutionTriggerSource = ExecutionTriggerSource.MANUAL,
        trigger_commit_sha: str | None = None,
    ) -> JobExecution:
        """実行履歴を作成し、SSH ジョブの完了まで処理する。"""

        execution = await self.create_pending(
            job_id,
            trigger_source=trigger_source,
            trigger_commit_sha=trigger_commit_sha,
        )
        return await self.execute_pending(execution.id)

    async def execute_pending(self, execution_id: int) -> JobExecution:
        """PENDING の実行を一度だけ RUNNING へ遷移させて処理する。"""

        result = await self.db.execute(
            select(JobExecution)
            .where(JobExecution.id == execution_id)
            .with_for_update()
        )
        execution = result.scalar_one_or_none()
        if not execution:
            raise ExecutionNotFoundError(f"実行ID {execution_id} が見つかりません")
        if execution.status != ExecutionStatus.PENDING:
            return execution

        job = await self.job_service.get_by_id(execution.job_id, include_server=True)
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        await self.db.commit()

        try:
            exit_code, stdout, stderr = await ssh_service.execute_script(
                server=job.server,
                script=job.script,
            )
            execution.status = (
                ExecutionStatus.SUCCESS if exit_code == 0 else ExecutionStatus.FAILED
            )
            execution.exit_code = exit_code
            execution.stdout = stdout
            execution.stderr = stderr
            execution.finished_at = datetime.now(timezone.utc)
        except SSHConnectionError as error:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = str(error)
            execution.finished_at = datetime.now(timezone.utc)
        except SSHExecutionError as error:
            execution.status = (
                ExecutionStatus.TIMEOUT
                if "タイムアウト" in str(error)
                else ExecutionStatus.FAILED
            )
            execution.error_message = str(error)
            execution.finished_at = datetime.now(timezone.utc)
        except asyncio.CancelledError:
            execution.status = ExecutionStatus.CANCELLED
            execution.error_message = "アプリケーション停止により実行を中断しました"
            execution.finished_at = datetime.now(timezone.utc)
            await self.db.commit()
            raise
        except Exception as error:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = f"予期しないエラー: {error}"
            execution.finished_at = datetime.now(timezone.utc)
        finally:
            if execution.status != ExecutionStatus.CANCELLED:
                await self.db.commit()

        await self.db.refresh(execution)
        return execution

    async def cancel_execution(self, execution_id: int) -> JobExecution:
        execution = await self.get_by_id(execution_id)
        if execution.status == ExecutionStatus.RUNNING:
            execution.status = ExecutionStatus.CANCELLED
            execution.finished_at = datetime.now(timezone.utc)
            execution.error_message = "ユーザーによってキャンセルされました"
            await self.db.commit()
            await self.db.refresh(execution)
        return execution

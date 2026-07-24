"""GitHub branch を定期確認し、SHA 変更時にジョブを投入する。"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import credential_encryptor
from app.models.execution import (
    ExecutionStatus,
    ExecutionTriggerSource,
    JobExecution,
)
from app.models.job import Job, JobTriggerType
from app.services.execution_runner import execution_runner
from app.services.github_service import GitHubAPIError, GitHubBranchResult, GitHubService


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TriggerSnapshot:
    """API 呼び出し中に設定変更されたケースを識別するスナップショット。"""

    job_id: int
    repository: str
    branch: str
    token_encrypted: str | None
    etag: str | None


class GitHubPollingService:
    """設定済みジョブを一定間隔で確認するアプリ内ポーラー。"""

    def __init__(
        self,
        session_factory: Callable[..., Any] = AsyncSessionLocal,
        github_service: GitHubService | None = None,
        interval_seconds: int | None = None,
        execution_scheduler: Callable[[int], None] = execution_runner.schedule,
    ):
        self._session_factory = session_factory
        self._github_service = github_service or GitHubService()
        self._interval_seconds = (
            interval_seconds or settings.github_poll_interval_seconds
        )
        self._execution_scheduler = execution_scheduler
        self._runner: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._runner and not self._runner.done():
            return
        self._stop_event.clear()
        self._runner = asyncio.create_task(
            self._run(),
            name="github-branch-poller",
        )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._runner:
            self._runner.cancel()
            await asyncio.gather(self._runner, return_exceptions=True)
            self._runner = None

        await self._github_service.close()

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.poll_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("GitHub polling cycle failed")

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._interval_seconds,
                )
            except asyncio.TimeoutError:
                continue

    async def poll_once(self) -> None:
        """有効な全 GitHub トリガーを一度確認する。"""

        async with self._session_factory() as db:
            result = await db.execute(
                select(Job.id).where(Job.trigger_type == JobTriggerType.GITHUB_POLL)
            )
            job_ids = list(result.scalars().all())

        for job_id in job_ids:
            await self._poll_job(job_id)

    async def _poll_job(self, job_id: int) -> None:
        snapshot = await self._load_snapshot(job_id)
        if not snapshot:
            return

        try:
            token = (
                credential_encryptor.decrypt(snapshot.token_encrypted)
                if snapshot.token_encrypted
                else None
            )
        except Exception:
            await self._record_error(snapshot, "保存されたGitHubトークンを復号できません")
            return

        try:
            branch_result = await self._github_service.get_branch_head(
                repository=snapshot.repository,
                branch=snapshot.branch,
                token=token,
                etag=snapshot.etag,
            )
        except GitHubAPIError as error:
            await self._record_error(snapshot, str(error))
            return

        execution_id = await self._apply_result(snapshot, branch_result)
        if execution_id is not None:
            self._schedule_execution(execution_id)

    async def _load_snapshot(self, job_id: int) -> TriggerSnapshot | None:
        async with self._session_factory() as db:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if (
                not job
                or job.trigger_type != JobTriggerType.GITHUB_POLL
                or not job.github_repository
                or not job.github_branch
            ):
                return None
            return TriggerSnapshot(
                job_id=job.id,
                repository=job.github_repository,
                branch=job.github_branch,
                token_encrypted=job.github_token_encrypted,
                etag=job.github_etag,
            )

    async def _record_error(self, snapshot: TriggerSnapshot, message: str) -> None:
        async with self._session_factory() as db:
            job = await self._lock_matching_job(db, snapshot)
            if not job:
                return
            job.github_last_checked_at = datetime.now(timezone.utc)
            job.github_last_error = message
            await db.commit()

    async def _apply_result(
        self,
        snapshot: TriggerSnapshot,
        branch_result: GitHubBranchResult,
    ) -> int | None:
        async with self._session_factory() as db:
            job = await self._lock_matching_job(db, snapshot)
            if not job:
                return None

            job.github_last_checked_at = datetime.now(timezone.utc)
            job.github_last_error = None
            job.github_etag = branch_result.etag
            if branch_result.not_modified:
                await db.commit()
                return None

            current_sha = branch_result.sha
            if current_sha is None:
                job.github_last_error = "GitHub APIからcommit SHAを取得できませんでした"
                await db.commit()
                return None

            previous_sha = job.github_last_commit_sha
            job.github_last_commit_sha = current_sha

            execution = None
            if previous_sha is not None and previous_sha != current_sha:
                execution = JobExecution(
                    job_id=job.id,
                    status=ExecutionStatus.PENDING,
                    trigger_source=ExecutionTriggerSource.GITHUB_POLL,
                    trigger_commit_sha=current_sha,
                )
                db.add(execution)

            # Job row の FOR UPDATE により、複数 Backend からの重複投入を防ぐ。
            await db.commit()
            if execution is None:
                return None
            await db.refresh(execution)
            return execution.id

    async def _lock_matching_job(self, db: Any, snapshot: TriggerSnapshot) -> Job | None:
        result = await db.execute(
            select(Job).where(Job.id == snapshot.job_id).with_for_update()
        )
        job = result.scalar_one_or_none()
        if (
            not job
            or job.trigger_type != JobTriggerType.GITHUB_POLL
            or job.github_repository != snapshot.repository
            or job.github_branch != snapshot.branch
            or job.github_token_encrypted != snapshot.token_encrypted
        ):
            return None
        return job

    def _schedule_execution(self, execution_id: int) -> None:
        self._execution_scheduler(execution_id)

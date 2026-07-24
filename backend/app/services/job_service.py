"""ジョブ定義の CRUD とトリガー設定を管理する。"""

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import credential_encryptor
from app.models.job import GitHubTokenSource, Job, JobTriggerType
from app.schemas.job import JobCreate, JobUpdate
from app.services.github_token_service import GitHubTokenService
from app.services.server_service import ServerService


class JobNotFoundError(Exception):
    """ジョブが見つからない。"""


class JobTriggerConfigurationError(Exception):
    """ジョブトリガー設定が不完全。"""


class JobService:
    """ジョブ管理サービス。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.server_service = ServerService(db)
        self.github_token_service = GitHubTokenService(db)

    async def get_all(self, include_server: bool = False) -> List[Job]:
        query = select(Job)
        if include_server:
            query = query.options(selectinload(Job.server))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, job_id: int, include_server: bool = False) -> Job:
        query = select(Job).where(Job.id == job_id)
        if include_server:
            query = query.options(selectinload(Job.server))
        result = await self.db.execute(query)
        job = result.scalar_one_or_none()
        if not job:
            raise JobNotFoundError(f"ジョブID {job_id} が見つかりません")
        return job

    async def get_by_server_id(
        self,
        server_id: int,
        include_server: bool = False,
    ) -> List[Job]:
        query = select(Job).where(Job.server_id == server_id)
        if include_server:
            query = query.options(selectinload(Job.server))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, job_data: JobCreate) -> Job:
        await self.server_service.get_by_id(job_data.server_id)

        trigger_type = job_data.trigger_type
        repository = job_data.github_repository
        branch = job_data.github_branch
        self._validate_trigger(trigger_type, repository, branch)

        token_source = job_data.github_token_source
        token_encrypted = None
        if trigger_type == JobTriggerType.GITHUB_POLL:
            await self._validate_token_source(
                token_source,
                has_job_token=bool(job_data.github_token),
            )
        if (
            trigger_type == JobTriggerType.GITHUB_POLL
            and token_source == GitHubTokenSource.JOB
            and job_data.github_token
        ):
            token_encrypted = credential_encryptor.encrypt(job_data.github_token)

        if trigger_type == JobTriggerType.MANUAL:
            repository = None
            branch = None
            token_source = GitHubTokenSource.NONE

        job = Job(
            name=job_data.name,
            description=job_data.description,
            script=job_data.script,
            server_id=job_data.server_id,
            trigger_type=trigger_type,
            github_repository=repository,
            github_branch=branch,
            github_token_source=token_source,
            github_token_encrypted=token_encrypted,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def update(self, job_id: int, job_data: JobUpdate) -> Job:
        job = await self.get_by_id(job_id)
        update_dict = job_data.model_dump(exclude_unset=True)

        if "server_id" in update_dict:
            await self.server_service.get_by_id(update_dict["server_id"])

        token_was_supplied = "github_token" in update_dict
        token = update_dict.pop("github_token", None)
        token_source_was_supplied = "github_token_source" in update_dict
        token_source = update_dict.pop(
            "github_token_source",
            job.github_token_source,
        )
        if token_was_supplied and not token_source_was_supplied:
            token_source = (
                GitHubTokenSource.JOB if token else GitHubTokenSource.NONE
            )
        trigger_type = update_dict.get("trigger_type", job.trigger_type)
        repository = update_dict.get("github_repository", job.github_repository)
        branch = update_dict.get("github_branch", job.github_branch)
        self._validate_trigger(trigger_type, repository, branch)
        if trigger_type == JobTriggerType.GITHUB_POLL:
            await self._validate_token_source(
                token_source,
                has_job_token=(
                    bool(token)
                    if token_was_supplied
                    else bool(job.github_token_encrypted)
                ),
            )

        trigger_target_changed = (
            trigger_type != job.trigger_type
            or repository != job.github_repository
            or branch != job.github_branch
        )

        for key, value in update_dict.items():
            if hasattr(job, key):
                setattr(job, key, value)

        if trigger_type == JobTriggerType.MANUAL:
            job.github_repository = None
            job.github_branch = None
            job.github_token_source = GitHubTokenSource.NONE
            job.github_token_encrypted = None
            trigger_target_changed = True
        else:
            job.github_token_source = token_source
            if token_source != GitHubTokenSource.JOB:
                job.github_token_encrypted = None
            elif token_was_supplied and token:
                job.github_token_encrypted = credential_encryptor.encrypt(token)

        if trigger_target_changed:
            # 新しい監視対象では、初回ポーリングを基準 SHA の記録だけにする。
            job.github_last_commit_sha = None
            job.github_etag = None
            job.github_last_checked_at = None
            job.github_last_error = None

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def delete(self, job_id: int) -> None:
        job = await self.get_by_id(job_id)
        await self.db.delete(job)
        await self.db.commit()

    @staticmethod
    def _validate_trigger(
        trigger_type: JobTriggerType,
        repository: str | None,
        branch: str | None,
    ) -> None:
        if trigger_type == JobTriggerType.GITHUB_POLL and (
            not repository or not branch
        ):
            raise JobTriggerConfigurationError(
                "GitHubトリガーにはリポジトリとブランチが必要です"
            )

    async def _validate_token_source(
        self,
        token_source: GitHubTokenSource,
        *,
        has_job_token: bool,
    ) -> None:
        if token_source == GitHubTokenSource.JOB and not has_job_token:
            raise JobTriggerConfigurationError(
                "ジョブ固有トークンを入力してください"
            )
        if (
            token_source == GitHubTokenSource.SHARED
            and await self.github_token_service.get(for_update=True) is None
        ):
            raise JobTriggerConfigurationError(
                "共通GitHubトークンが設定されていません"
            )

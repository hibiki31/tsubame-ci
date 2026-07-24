import unittest
from unittest.mock import AsyncMock, Mock

from app.core.security import credential_encryptor
from app.models.github_token import GitHubToken
from app.models.execution import JobExecution
from app.models.job import GitHubTokenSource, Job, JobTriggerType
from app.schemas.job import JobCreate, JobUpdate
from app.services.job_service import JobService, JobTriggerConfigurationError


class JobServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_all_with_latest_execution_uses_one_correlated_record(
        self,
    ) -> None:
        db = AsyncMock()
        result = Mock()
        job = Mock(spec=Job)
        execution = Mock(spec=JobExecution)
        result.all.return_value = [(job, execution)]
        db.execute.return_value = result
        service = JobService(db)

        items = await service.get_all_with_latest_execution(
            server_id=3,
            include_server=True,
        )

        self.assertEqual(items, [(job, execution)])
        statement = db.execute.await_args.args[0]
        sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("LEFT OUTER JOIN job_executions", sql)
        self.assertIn(
            "ORDER BY job_executions.created_at DESC, job_executions.id DESC",
            sql,
        )
        self.assertIn("WHERE jobs.server_id = 3", sql)

    async def test_create_encrypts_github_token_before_persistence(self) -> None:
        db = AsyncMock()
        db.add = Mock()
        service = JobService(db)
        service.server_service.get_by_id = AsyncMock()
        request = JobCreate(
            name="deploy",
            script="./deploy.sh",
            server_id=1,
            trigger_type=JobTriggerType.GITHUB_POLL,
            github_repository="acme/private-project",
            github_branch="main",
            github_token="github-plain-token",
        )

        job = await service.create(request)

        self.assertNotEqual(job.github_token_encrypted, "github-plain-token")
        self.assertEqual(
            credential_encryptor.decrypt(job.github_token_encrypted),
            "github-plain-token",
        )
        self.assertTrue(job.github_token_configured)
        self.assertEqual(job.github_token_source, GitHubTokenSource.JOB)
        db.add.assert_called_once_with(job)
        db.commit.assert_awaited_once_with()

    async def test_create_can_reference_shared_github_token(self) -> None:
        db = AsyncMock()
        db.add = Mock()
        service = JobService(db)
        service.server_service.get_by_id = AsyncMock()
        service.github_token_service.get = AsyncMock(
            return_value=GitHubToken(id=1, token_encrypted="encrypted")
        )
        request = JobCreate(
            name="deploy",
            script="./deploy.sh",
            server_id=1,
            trigger_type=JobTriggerType.GITHUB_POLL,
            github_repository="acme/private-project",
            github_branch="main",
            github_token_source=GitHubTokenSource.SHARED,
        )

        job = await service.create(request)

        self.assertEqual(job.github_token_source, GitHubTokenSource.SHARED)
        self.assertIsNone(job.github_token_encrypted)
        service.github_token_service.get.assert_awaited_once_with(for_update=True)

    async def test_create_rejects_missing_shared_github_token(self) -> None:
        db = AsyncMock()
        service = JobService(db)
        service.server_service.get_by_id = AsyncMock()
        service.github_token_service.get = AsyncMock(return_value=None)
        request = JobCreate(
            name="deploy",
            script="./deploy.sh",
            server_id=1,
            trigger_type=JobTriggerType.GITHUB_POLL,
            github_repository="acme/private-project",
            github_branch="main",
            github_token_source=GitHubTokenSource.SHARED,
        )

        with self.assertRaises(JobTriggerConfigurationError):
            await service.create(request)

    async def test_update_switches_job_token_to_shared_token(self) -> None:
        db = AsyncMock()
        service = JobService(db)
        job = Job(
            id=1,
            name="deploy",
            script="./deploy.sh",
            server_id=1,
            trigger_type=JobTriggerType.GITHUB_POLL,
            github_repository="acme/private-project",
            github_branch="main",
            github_token_source=GitHubTokenSource.JOB,
            github_token_encrypted=credential_encryptor.encrypt("job-token"),
        )
        service.get_by_id = AsyncMock(return_value=job)
        service.github_token_service.get = AsyncMock(
            return_value=GitHubToken(id=1, token_encrypted="shared-encrypted")
        )

        updated = await service.update(
            job.id,
            JobUpdate(github_token_source=GitHubTokenSource.SHARED),
        )

        self.assertEqual(updated.github_token_source, GitHubTokenSource.SHARED)
        self.assertIsNone(updated.github_token_encrypted)
        service.github_token_service.get.assert_awaited_once_with(for_update=True)


if __name__ == "__main__":
    unittest.main()

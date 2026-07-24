import unittest
from unittest.mock import AsyncMock

from app.core.security import credential_encryptor
from app.models.execution import ExecutionTriggerSource
from app.models.job import GitHubTokenSource, Job, JobTriggerType
from app.services.github_polling_service import GitHubPollingService, TriggerSnapshot
from app.services.github_service import GitHubBranchResult


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, job: Job):
        self.job = job
        self.executions = []
        self.next_execution_id = 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, statement):
        return FakeResult(self.job)

    def add(self, execution):
        execution.id = self.next_execution_id
        self.next_execution_id += 1
        self.executions.append(execution)

    async def commit(self):
        return None

    async def refresh(self, value):
        return None


class QueueSession(FakeSession):
    def __init__(self, job: Job, extra_results: list[object]):
        super().__init__(job)
        self.results = [job, *extra_results]

    async def execute(self, statement):
        return FakeResult(self.results.pop(0))


class GitHubPollingServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.job = Job(
            id=10,
            name="deploy",
            script="./deploy.sh",
            server_id=1,
            trigger_type=JobTriggerType.GITHUB_POLL,
            github_repository="acme/project",
            github_branch="main",
            github_token_source=GitHubTokenSource.NONE,
            github_token_encrypted=None,
            github_last_commit_sha=None,
        )
        self.session = FakeSession(self.job)
        github_service = AsyncMock()
        github_service.close = AsyncMock()
        self.poller = GitHubPollingService(
            session_factory=lambda: self.session,
            github_service=github_service,
            interval_seconds=60,
        )
        self.snapshot = TriggerSnapshot(
            job_id=10,
            repository="acme/project",
            branch="main",
            token_encrypted=None,
            etag=None,
        )

    async def test_first_poll_records_baseline_without_execution(self) -> None:
        execution_id = await self.poller._apply_result(
            self.snapshot,
            GitHubBranchResult(sha="a" * 40, etag='"first"'),
        )

        self.assertIsNone(execution_id)
        self.assertEqual(self.job.github_last_commit_sha, "a" * 40)
        self.assertEqual(self.session.executions, [])

    async def test_changed_sha_creates_one_github_execution(self) -> None:
        self.job.github_last_commit_sha = "a" * 40

        first_execution_id = await self.poller._apply_result(
            self.snapshot,
            GitHubBranchResult(sha="b" * 40, etag='"second"'),
        )
        duplicate_execution_id = await self.poller._apply_result(
            self.snapshot,
            GitHubBranchResult(sha="b" * 40, etag='"second"'),
        )

        self.assertEqual(first_execution_id, 1)
        self.assertIsNone(duplicate_execution_id)
        self.assertEqual(len(self.session.executions), 1)
        execution = self.session.executions[0]
        self.assertEqual(execution.trigger_source, ExecutionTriggerSource.GITHUB_POLL)
        self.assertEqual(execution.trigger_commit_sha, "b" * 40)
        self.assertEqual(execution.server_id_snapshot, self.job.server_id)
        self.assertEqual(execution.script_snapshot, self.job.script)

    async def test_load_snapshot_resolves_shared_token(self) -> None:
        encrypted = credential_encryptor.encrypt("shared-token")
        self.job.github_token_source = GitHubTokenSource.SHARED
        session = QueueSession(self.job, [encrypted])
        self.poller._session_factory = lambda: session

        snapshot = await self.poller._load_snapshot(self.job.id)

        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.token_source, GitHubTokenSource.SHARED)
        self.assertEqual(snapshot.token_encrypted, encrypted)
        self.assertIsNone(snapshot.job_token_encrypted)

    async def test_poll_uses_decrypted_shared_token(self) -> None:
        encrypted = credential_encryptor.encrypt("shared-token")
        snapshot = TriggerSnapshot(
            job_id=self.job.id,
            repository="acme/project",
            branch="main",
            token_encrypted=encrypted,
            etag=None,
            token_source=GitHubTokenSource.SHARED,
        )
        self.poller._load_snapshot = AsyncMock(return_value=snapshot)
        self.poller._apply_result = AsyncMock(return_value=None)
        self.poller._github_service.get_branch_head.return_value = (
            GitHubBranchResult(sha=None, etag='"same"', not_modified=True)
        )

        await self.poller._poll_job(self.job.id)

        self.poller._github_service.get_branch_head.assert_awaited_once_with(
            repository="acme/project",
            branch="main",
            token="shared-token",
            etag=None,
        )

    async def test_shared_token_rotation_discards_in_flight_result(self) -> None:
        self.job.github_token_source = GitHubTokenSource.SHARED
        session = QueueSession(self.job, ["new-encrypted-token"])
        snapshot = TriggerSnapshot(
            job_id=self.job.id,
            repository="acme/project",
            branch="main",
            token_encrypted="old-encrypted-token",
            etag=None,
            token_source=GitHubTokenSource.SHARED,
        )

        job = await self.poller._lock_matching_job(session, snapshot)

        self.assertIsNone(job)


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import AsyncMock

from app.models.execution import ExecutionTriggerSource
from app.models.job import Job, JobTriggerType
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


if __name__ == "__main__":
    unittest.main()

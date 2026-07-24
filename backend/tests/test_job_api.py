import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.api.v1.jobs import list_jobs
from app.models.execution import ExecutionStatus
from app.models.job import GitHubTokenSource, JobTriggerType
from app.models.server import AuthMethod


class JobApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_list_jobs_includes_latest_execution(self) -> None:
        created_at = datetime(2026, 7, 25, 3, 15, tzinfo=timezone.utc)
        server = SimpleNamespace(
            id=2,
            name="build-server",
            description=None,
            host="build.example.com",
            port=22,
            username="ci",
            auth_method=AuthMethod.KEY,
            created_at=created_at,
        )
        job = SimpleNamespace(
            id=5,
            name="frontend-build",
            description=None,
            script="npm run build",
            server_id=server.id,
            trigger_type=JobTriggerType.MANUAL,
            github_token_source=GitHubTokenSource.NONE,
            github_token_configured=False,
            created_at=created_at,
            server=server,
        )
        execution = SimpleNamespace(
            id=9,
            status=ExecutionStatus.SUCCESS,
            created_at=created_at,
        )
        service = AsyncMock()
        service.get_all_with_latest_execution.return_value = [(job, execution)]

        result = await list_jobs(server_id=None, service=service)

        self.assertEqual(result[0].latest_execution.id, execution.id)
        self.assertEqual(
            result[0].latest_execution.status,
            ExecutionStatus.SUCCESS,
        )
        service.get_all_with_latest_execution.assert_awaited_once_with(
            server_id=None,
            include_server=True,
        )


if __name__ == "__main__":
    unittest.main()

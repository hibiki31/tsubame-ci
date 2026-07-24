import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models.execution import ExecutionStatus
from app.services.execution_service import ExecutionService
from app.services.ssh_service import ssh_service


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class ExecutionServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_execute_pending_persists_streamed_output(self) -> None:
        execution = SimpleNamespace(
            id=5,
            job_id=2,
            status=ExecutionStatus.PENDING,
            started_at=None,
            finished_at=None,
            exit_code=None,
            stdout=None,
            stderr=None,
            error_message=None,
        )
        db = SimpleNamespace(
            execute=AsyncMock(return_value=FakeResult(execution)),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )
        service = ExecutionService(db)
        service.job_service.get_by_id = AsyncMock(
            return_value=SimpleNamespace(
                script="echo first; echo warning >&2",
                server=SimpleNamespace(),
            )
        )

        async def stream_output(*, server, script, on_output):
            await on_output("stdout", "first\n")
            await on_output("stdout", "second\n")
            await on_output("stderr", "warning\n")
            return 0, "first\nsecond\n", "warning\n"

        with patch.object(
            ssh_service,
            "execute_script",
            AsyncMock(side_effect=stream_output),
        ):
            result = await service.execute_pending(execution.id)

        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertEqual(result.stdout, "first\nsecond\n")
        self.assertEqual(result.stderr, "warning\n")
        self.assertEqual(result.exit_code, 0)
        self.assertGreaterEqual(db.commit.await_count, 5)
        db.refresh.assert_awaited_once_with(execution)


if __name__ == "__main__":
    unittest.main()

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from app.services.execution_runner import ExecutionRunner


class FakeScalars:
    def all(self):
        return [7, 8]


class FakeResult:
    def scalars(self):
        return FakeScalars()


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def execute(self, statement):
        return FakeResult()


class ExecutionRunnerTest(unittest.IsolatedAsyncioTestCase):
    async def test_start_reschedules_persisted_active_executions(self) -> None:
        runner = ExecutionRunner(session_factory=FakeSession)
        runner.schedule = Mock()

        await runner.start()

        self.assertEqual(
            [call.args[0] for call in runner.schedule.call_args_list],
            [7, 8],
        )

    async def test_schedule_deduplicates_active_execution(self) -> None:
        runner = ExecutionRunner()
        release = asyncio.Event()

        async def wait_for_release(execution_id: int) -> None:
            self.assertEqual(execution_id, 42)
            await release.wait()

        runner._execute = AsyncMock(side_effect=wait_for_release)

        runner.schedule(42)
        runner.schedule(42)
        await asyncio.sleep(0)

        runner._execute.assert_awaited_once_with(42)
        release.set()
        await asyncio.sleep(0)
        await runner.stop()

    async def test_stop_cancels_owned_execution(self) -> None:
        runner = ExecutionRunner()
        started = asyncio.Event()

        async def run_forever(execution_id: int) -> None:
            self.assertEqual(execution_id, 7)
            started.set()
            await asyncio.Event().wait()

        runner._execute = AsyncMock(side_effect=run_forever)

        runner.schedule(7)
        await started.wait()
        await runner.stop()

        self.assertEqual(runner._tasks, {})


if __name__ == "__main__":
    unittest.main()

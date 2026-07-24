import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models.execution import ExecutionStatus
from app.services.execution_service import ExecutionService
from app.services.remote_execution_service import (
    RemoteExecutionSnapshot,
    RemoteExecutionState,
    RemoteLogChunk,
)
from app.services.ssh_service import SSHConnectionError


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


def execution_record(**overrides):
    values = {
        "id": 5,
        "job_id": 2,
        "status": ExecutionStatus.PENDING,
        "server_id_snapshot": 3,
        "script_snapshot": "echo completed",
        "remote_execution_id": None,
        "remote_process_id": None,
        "stdout_offset": 0,
        "stderr_offset": 0,
        "stdout": None,
        "stderr": None,
        "started_at": None,
        "finished_at": None,
        "last_synced_at": None,
        "tracking_error": None,
        "cancel_requested_at": None,
        "exit_code": None,
        "error_message": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class ExecutionServiceTest(unittest.IsolatedAsyncioTestCase):
    def make_service(self, execution):
        db = SimpleNamespace(
            execute=AsyncMock(return_value=FakeResult(execution)),
            commit=AsyncMock(),
            refresh=AsyncMock(),
        )
        return ExecutionService(db), db

    async def test_claim_persists_remote_id_before_start(self) -> None:
        execution = execution_record()
        service, db = self.make_service(execution)

        result = await service._claim_or_resume(execution.id)

        self.assertEqual(result.status, ExecutionStatus.RUNNING)
        self.assertRegex(result.remote_execution_id, r"^[0-9a-f]{32}$")
        self.assertIsNotNone(result.started_at)
        db.commit.assert_awaited_once_with()

    async def test_legacy_running_execution_is_failed_instead_of_staying_stuck(
        self,
    ) -> None:
        execution = execution_record(
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        service, _ = self.make_service(execution)

        result = await service._claim_or_resume(execution.id)

        self.assertEqual(result.status, ExecutionStatus.FAILED)
        self.assertIn("再追跡情報がない", result.error_message)
        self.assertIsNotNone(result.finished_at)

    async def test_finished_snapshot_persists_all_logs_and_exit_status(self) -> None:
        execution = execution_record(
            status=ExecutionStatus.RUNNING,
            remote_execution_id="a" * 32,
            started_at=datetime.now(timezone.utc),
        )
        service, db = self.make_service(execution)
        finished_at = datetime.now(timezone.utc)
        snapshot = RemoteExecutionSnapshot(
            state=RemoteExecutionState.FINISHED,
            process_id=4321,
            exit_code=0,
            finished_at=finished_at,
            stdout=RemoteLogChunk("completed\n", 10, True),
            stderr=RemoteLogChunk("warning\n", 8, True),
            alive=False,
        )

        terminal = await service._apply_snapshot(
            execution.id,
            0,
            0,
            snapshot,
            timed_out=False,
        )

        self.assertTrue(terminal)
        self.assertEqual(execution.status, ExecutionStatus.SUCCESS)
        self.assertEqual(execution.stdout, "completed\n")
        self.assertEqual(execution.stderr, "warning\n")
        self.assertEqual(execution.stdout_offset, 10)
        self.assertEqual(execution.stderr_offset, 8)
        self.assertEqual(execution.remote_process_id, 4321)
        self.assertEqual(execution.finished_at, finished_at)
        db.commit.assert_awaited_once_with()

    async def test_stale_snapshot_does_not_duplicate_log(self) -> None:
        execution = execution_record(
            status=ExecutionStatus.RUNNING,
            remote_execution_id="b" * 32,
            stdout="already synced\n",
            stdout_offset=15,
        )
        service, _ = self.make_service(execution)
        snapshot = RemoteExecutionSnapshot(
            state=RemoteExecutionState.RUNNING,
            process_id=10,
            exit_code=None,
            finished_at=None,
            stdout=RemoteLogChunk("already synced\n", 15, False),
            stderr=RemoteLogChunk("", 0, True),
            alive=True,
        )

        terminal = await service._apply_snapshot(
            execution.id,
            0,
            0,
            snapshot,
            timed_out=False,
        )

        self.assertFalse(terminal)
        self.assertEqual(execution.stdout, "already synced\n")
        self.assertEqual(execution.stdout_offset, 15)

    async def test_cancel_running_execution_is_durable_request(self) -> None:
        execution = execution_record(
            status=ExecutionStatus.RUNNING,
            remote_execution_id="c" * 32,
        )
        service, db = self.make_service(execution)

        result = await service.cancel_execution(execution.id)

        self.assertEqual(result.status, ExecutionStatus.RUNNING)
        self.assertIsNotNone(result.cancel_requested_at)
        db.refresh.assert_awaited_once_with(execution)

    async def test_tracking_retries_after_temporary_ssh_failure(self) -> None:
        execution = execution_record(
            status=ExecutionStatus.RUNNING,
            remote_execution_id="d" * 32,
            started_at=datetime.now(timezone.utc),
        )
        service, db = self.make_service(execution)
        service.poll_interval = 0
        service.reconnect_max_interval = 0
        service._reload_execution = AsyncMock(return_value=execution)
        service.server_service.get_by_id = AsyncMock(return_value=object())
        service.remote_execution = SimpleNamespace(
            ensure_started=AsyncMock(
                side_effect=[SSHConnectionError("temporary"), None]
            ),
            request_cancel=AsyncMock(),
            snapshot=AsyncMock(return_value=object()),
        )
        service._record_tracking_error = AsyncMock()
        service._apply_snapshot = AsyncMock(return_value=True)

        with patch("app.services.execution_service.asyncio.sleep", AsyncMock()):
            await service._track_remote(execution.id)

        self.assertEqual(service.remote_execution.ensure_started.await_count, 2)
        service._record_tracking_error.assert_awaited_once_with(
            execution.id,
            "temporary",
        )
        service._apply_snapshot.assert_awaited_once()
        self.assertGreaterEqual(db.commit.await_count, 2)


if __name__ == "__main__":
    unittest.main()

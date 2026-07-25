import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.api.v1.executions import (
    cancel_execution,
    execute_ad_hoc,
    execution_runner,
    get_execution,
    list_executions,
)
from app.models.execution import ExecutionStatus
from app.schemas.execution import AdHocExecutionCreateRequest


class ExecutionApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_list_executions_loads_job_for_display(self) -> None:
        service = AsyncMock()
        service.get_all.return_value = []

        result = await list_executions(
            limit=50,
            offset=0,
            job_id=None,
            service=service,
        )

        self.assertEqual(result, [])
        service.get_all.assert_awaited_once_with(
            limit=50,
            offset=0,
            include_job=True,
        )

    async def test_get_execution_loads_job_for_display(self) -> None:
        execution = object()
        service = AsyncMock()
        service.get_by_id.return_value = execution

        result = await get_execution(12, service=service)

        self.assertIs(result, execution)
        service.get_by_id.assert_awaited_once_with(12, include_job=True)

    async def test_cancel_keeps_running_execution_scheduled_for_retry(self) -> None:
        execution = SimpleNamespace(id=12, status=ExecutionStatus.RUNNING)
        service = AsyncMock()
        service.cancel_execution.return_value = execution

        with patch.object(execution_runner, "schedule") as schedule:
            result = await cancel_execution(12, service=service)

        self.assertIs(result, execution)
        schedule.assert_called_once_with(12)

    async def test_ad_hoc_execution_is_persisted_and_scheduled(self) -> None:
        pending = SimpleNamespace(id=13)
        loaded = SimpleNamespace(id=13, job_id=None)
        service = AsyncMock()
        service.create_ad_hoc_pending.return_value = pending
        service.get_by_id.return_value = loaded
        request = AdHocExecutionCreateRequest(
            name="月次集計",
            server_id=4,
            script="./monthly.sh",
        )

        with patch.object(execution_runner, "schedule") as schedule:
            result = await execute_ad_hoc(request, service=service)

        self.assertIs(result, loaded)
        service.create_ad_hoc_pending.assert_awaited_once_with(
            name="月次集計",
            server_id=4,
            script="./monthly.sh",
        )
        schedule.assert_called_once_with(13)
        service.get_by_id.assert_awaited_once_with(13, include_job=True)


if __name__ == "__main__":
    unittest.main()

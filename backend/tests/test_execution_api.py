import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.api.v1.executions import (
    cancel_execution,
    execution_runner,
    get_execution,
    list_executions,
)
from app.models.execution import ExecutionStatus


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


if __name__ == "__main__":
    unittest.main()

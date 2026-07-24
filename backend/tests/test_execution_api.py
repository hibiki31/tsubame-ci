import unittest
from unittest.mock import AsyncMock

from app.api.v1.executions import get_execution, list_executions


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


if __name__ == "__main__":
    unittest.main()

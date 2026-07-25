import unittest
from unittest.mock import AsyncMock

from fastapi import HTTPException

from app.api.v1.servers import delete_server
from app.services.server_service import ServerHasActiveExecutionsError


class ServerApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_delete_maps_active_execution_to_conflict(self) -> None:
        service = AsyncMock()
        service.delete.side_effect = ServerHasActiveExecutionsError(
            "実行中の履歴があります"
        )

        with self.assertRaises(HTTPException) as context:
            await delete_server(12, service=service)

        self.assertEqual(context.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()

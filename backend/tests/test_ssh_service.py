import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.models.server import AuthMethod
from app.services.ssh_service import SSHExecutionError, SSHService


class SSHServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = SSHService()
        self.connection = SimpleNamespace(
            run=AsyncMock(),
            close=Mock(return_value=None),
            wait_closed=AsyncMock(),
        )
        self.service._create_connection = AsyncMock(return_value=self.connection)
        self.server = SimpleNamespace(
            host="example.test",
            port=22,
            username="runner",
            auth_method=AuthMethod.PASSWORD,
            password_encrypted=None,
            private_key_encrypted=None,
        )

    async def test_execute_script_closes_connection_after_success(self) -> None:
        self.connection.run.return_value = SimpleNamespace(
            exit_status=0,
            stdout="completed\n",
            stderr="",
        )

        result = await self.service.execute_script(self.server, "echo completed")

        self.assertEqual(result, (0, "completed\n", ""))
        self.connection.close.assert_called_once_with()
        self.connection.wait_closed.assert_awaited_once_with()

    async def test_execute_script_closes_connection_after_timeout(self) -> None:
        self.connection.run.side_effect = asyncio.TimeoutError

        with self.assertRaisesRegex(SSHExecutionError, "タイムアウト"):
            await self.service.execute_script(self.server, "sleep 999")

        self.connection.close.assert_called_once_with()
        self.connection.wait_closed.assert_awaited_once_with()

    async def test_connection_check_closes_connection_after_success(self) -> None:
        self.connection.run.return_value = SimpleNamespace()

        success, message = await self.service.test_connection(
            host="example.test",
            port=22,
            username="runner",
            auth_method=AuthMethod.PASSWORD,
            password="secret",
        )

        self.assertTrue(success)
        self.assertEqual(message, "接続に成功しました")
        self.connection.close.assert_called_once_with()
        self.connection.wait_closed.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()

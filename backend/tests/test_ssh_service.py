import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.models.server import AuthMethod
from app.services.ssh_service import SSHConnectionError, SSHExecutionError, SSHService


class SSHServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.service = SSHService()
        self.process = SimpleNamespace(
            stdout=SimpleNamespace(
                read=AsyncMock(side_effect=["completed\n", ""]),
            ),
            stderr=SimpleNamespace(
                read=AsyncMock(side_effect=["warning\n", ""]),
            ),
            exit_status=0,
            wait_closed=AsyncMock(),
        )
        self.connection = SimpleNamespace(
            run=AsyncMock(),
            create_process=AsyncMock(return_value=self.process),
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
        result = await self.service.execute_script(self.server, "echo completed")

        self.assertEqual(result, (0, "completed\n", "warning\n"))
        self.connection.create_process.assert_awaited_once_with("echo completed")
        self.process.wait_closed.assert_awaited_once_with()
        self.connection.close.assert_called_once_with()
        self.connection.wait_closed.assert_awaited_once_with()

    async def test_execute_script_notifies_output_as_it_arrives(self) -> None:
        on_output = AsyncMock()

        await self.service.execute_script(
            self.server,
            "echo completed",
            on_output=on_output,
        )

        on_output.assert_any_await("stdout", "completed\n")
        on_output.assert_any_await("stderr", "warning\n")
        self.assertEqual(on_output.await_count, 2)

    async def test_execute_script_closes_connection_after_timeout(self) -> None:
        self.process.stdout.read.side_effect = asyncio.TimeoutError

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

    async def test_connection_check_returns_connection_error_without_wrapping(self) -> None:
        self.service._create_connection.side_effect = SSHConnectionError("接続タイムアウト（30秒）")

        success, message = await self.service.test_connection(
            host="example.test",
            port=22,
            username="runner",
            auth_method=AuthMethod.PASSWORD,
            password="secret",
        )

        self.assertFalse(success)
        self.assertEqual(message, "接続タイムアウト（30秒）")

    async def test_inspect_server_parses_inventory_and_closes_connection(self) -> None:
        self.connection.run.return_value = SimpleNamespace(
            stdout="""ignored output
TSUBAME_HOSTNAME=ci-runner-01
TSUBAME_ARCHITECTURE=x86_64
TSUBAME_CPU_MODEL=Example CPU
TSUBAME_CPU_CORES=8
TSUBAME_MEMORY_TOTAL_BYTES=17179869184
TSUBAME_DISK_TOTAL_BYTES=107374182400
TSUBAME_OS_NAME=Example Linux
TSUBAME_OS_VERSION=1.0 = Stable
TSUBAME_KERNEL=Linux 6.8.0
TSUBAME_PACKAGE_MANAGER=apt
TSUBAME_PYTHON_VERSION=Python 3.12.1
TSUBAME_GIT_VERSION=git version 2.45.0
"""
        )

        result = await self.service.inspect_server(self.server)

        self.assertGreaterEqual(result.latency_ms, 0)
        self.assertEqual(result.hardware_info["cpu_cores"], 8)
        self.assertEqual(result.hardware_info["memory_total_bytes"], 17179869184)
        self.assertEqual(result.software_info["os_version"], "1.0 = Stable")
        self.assertIsNone(result.warning)
        self.connection.close.assert_called_once_with()
        self.connection.wait_closed.assert_awaited_once_with()

    async def test_inspect_server_warns_when_inventory_is_empty(self) -> None:
        self.connection.run.return_value = SimpleNamespace(stdout="")

        result = await self.service.inspect_server(self.server)

        self.assertEqual(result.hardware_info, {})
        self.assertEqual(result.software_info, {})
        self.assertIn("構成情報を取得できません", result.warning or "")
        self.connection.close.assert_called_once_with()
        self.connection.wait_closed.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()

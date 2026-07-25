import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.models.server import ServerConnectionStatus
from app.services.server_service import (
    ServerHasActiveExecutionsError,
    ServerService,
)
from app.services.ssh_service import ServerInspectionResult, SSHConnectionError


class ServerServiceMonitoringTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.db = AsyncMock()
        self.ssh = SimpleNamespace(inspect_server=AsyncMock())
        self.service = ServerService(self.db, ssh=self.ssh)
        self.server = SimpleNamespace(
            connection_status=ServerConnectionStatus.UNKNOWN.value,
            last_checked_at=None,
            last_check_latency_ms=None,
            last_check_error=None,
            hardware_info={"hostname": "previous-host"},
            software_info={"os_name": "Previous Linux"},
            inventory_collected_at=None,
        )
        self.service.get_by_id = AsyncMock(return_value=self.server)

    async def test_check_connection_saves_online_status_and_inventory(self) -> None:
        self.ssh.inspect_server.return_value = ServerInspectionResult(
            latency_ms=42,
            hardware_info={"hostname": "runner", "cpu_cores": 4},
            software_info={"os_name": "Example Linux"},
        )

        result = await self.service.check_connection(10)

        self.assertIs(result, self.server)
        self.assertEqual(self.server.connection_status, ServerConnectionStatus.ONLINE.value)
        self.assertEqual(self.server.last_check_latency_ms, 42)
        self.assertEqual(self.server.hardware_info["cpu_cores"], 4)
        self.assertEqual(self.server.inventory_collected_at, self.server.last_checked_at)
        self.db.commit.assert_awaited_once_with()
        self.db.refresh.assert_awaited_once_with(self.server)

    async def test_check_connection_keeps_last_inventory_when_offline(self) -> None:
        previous_hardware = self.server.hardware_info
        previous_software = self.server.software_info
        self.ssh.inspect_server.side_effect = SSHConnectionError("接続できません")

        await self.service.check_connection(11)

        self.assertEqual(self.server.connection_status, ServerConnectionStatus.OFFLINE.value)
        self.assertIsNone(self.server.last_check_latency_ms)
        self.assertEqual(self.server.last_check_error, "接続できません")
        self.assertIs(self.server.hardware_info, previous_hardware)
        self.assertIs(self.server.software_info, previous_software)
        self.db.commit.assert_awaited_once_with()

    async def test_delete_rejects_server_with_active_execution(self) -> None:
        self.db.execute.return_value = SimpleNamespace(
            scalar_one_or_none=lambda: 42,
        )

        with self.assertRaises(ServerHasActiveExecutionsError):
            await self.service.delete(12)

        self.db.delete.assert_not_awaited()
        self.db.commit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()

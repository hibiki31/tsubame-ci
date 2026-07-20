import asyncio
import unittest
from unittest.mock import AsyncMock

from app.services.server_monitor import ServerMonitor


class ServerMonitorTest(unittest.IsolatedAsyncioTestCase):
    async def test_start_runs_immediately_and_stop_cancels_wait(self) -> None:
        monitor = ServerMonitor(interval_seconds=3600, concurrency=1)
        monitor.run_once = AsyncMock()

        monitor.start()
        await asyncio.sleep(0)
        await monitor.stop()

        monitor.run_once.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()

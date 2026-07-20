"""登録サーバの定期接続監視"""
import asyncio
import logging
from contextlib import suppress

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.server import Server
from app.services.server_service import ServerNotFoundError, ServerService


logger = logging.getLogger(__name__)


class ServerMonitor:
    """一定間隔で全登録サーバのSSH接続と構成情報を更新する"""

    def __init__(self, interval_seconds: int, concurrency: int):
        self.interval_seconds = interval_seconds
        self.concurrency = concurrency
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="server-monitor")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("サーバ定期監視の実行に失敗しました")

            await asyncio.sleep(self.interval_seconds)

    async def run_once(self) -> None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Server.id))
            server_ids = list(result.scalars().all())

        semaphore = asyncio.Semaphore(self.concurrency)

        async def check(server_id: int) -> None:
            async with semaphore:
                async with AsyncSessionLocal() as db:
                    try:
                        await ServerService(db).check_connection(server_id)
                    except ServerNotFoundError:
                        logger.info("監視中に削除されたサーバをスキップしました: id=%s", server_id)
                    except Exception:
                        await db.rollback()
                        logger.exception("サーバ接続監視に失敗しました: id=%s", server_id)

        await asyncio.gather(*(check(server_id) for server_id in server_ids))


server_monitor = ServerMonitor(
    interval_seconds=settings.server_check_interval_seconds,
    concurrency=settings.server_check_concurrency,
)

"""DB に永続化したジョブ実行をアプリ内 task として管理する。"""

import asyncio
import logging
from typing import Any, Callable

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.execution import ExecutionStatus, JobExecution
from app.services.execution_service import ExecutionService


logger = logging.getLogger(__name__)


class ExecutionRunner:
    """実行 task の所有、再投入、終了処理を一箇所で管理する。"""

    def __init__(self, session_factory: Callable[..., Any] = AsyncSessionLocal):
        self._session_factory = session_factory
        self._tasks: dict[int, asyncio.Task[None]] = {}

    async def start(self) -> None:
        """プロセス停止後に残った PENDING 実行を再投入する。"""

        async with self._session_factory() as db:
            result = await db.execute(
                select(JobExecution.id).where(
                    JobExecution.status == ExecutionStatus.PENDING
                )
            )
            execution_ids = list(result.scalars().all())

        for execution_id in execution_ids:
            self.schedule(execution_id)

    async def stop(self) -> None:
        """所有している task を停止し、ExecutionService に状態保存させる。"""

        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    def schedule(self, execution_id: int) -> None:
        """未投入の実行をアプリ内 task へ投入する。"""

        current = self._tasks.get(execution_id)
        if current and not current.done():
            return

        task = asyncio.create_task(
            self._execute(execution_id),
            name=f"job-execution-{execution_id}",
        )
        self._tasks[execution_id] = task
        task.add_done_callback(
            lambda completed, target_id=execution_id: self._task_done(
                target_id,
                completed,
            )
        )

    async def _execute(self, execution_id: int) -> None:
        async with self._session_factory() as db:
            await ExecutionService(db).execute_pending(execution_id)

    def _task_done(
        self,
        execution_id: int,
        task: asyncio.Task[None],
    ) -> None:
        if self._tasks.get(execution_id) is task:
            self._tasks.pop(execution_id, None)
        if task.cancelled():
            return
        error = task.exception()
        if error:
            logger.error(
                "Job execution task failed",
                exc_info=(type(error), error, error.__traceback__),
            )


execution_runner = ExecutionRunner()

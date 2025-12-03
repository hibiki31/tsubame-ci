"""
API依存性注入
共通の依存関数を定義
"""
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.server_service import ServerService
from app.services.job_service import JobService
from app.services.execution_service import ExecutionService


async def get_server_service(
    db: AsyncSession = Depends(get_db)
) -> ServerService:
    """サーバサービスの依存性注入"""
    return ServerService(db)


async def get_job_service(
    db: AsyncSession = Depends(get_db)
) -> JobService:
    """ジョブサービスの依存性注入"""
    return JobService(db)


async def get_execution_service(
    db: AsyncSession = Depends(get_db)
) -> ExecutionService:
    """実行サービスの依存性注入"""
    return ExecutionService(db)

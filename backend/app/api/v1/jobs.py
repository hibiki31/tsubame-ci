"""
ジョブ管理API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List

from app.schemas.job import (
    JobCreate,
    JobListItemResponse,
    JobResponse,
    JobUpdate,
    JobWithServerResponse,
)
from app.schemas.execution import ExecutionResponse
from app.services.job_service import (
    JobService,
    JobNotFoundError,
    JobTriggerConfigurationError,
)
from app.services.server_service import ServerNotFoundError
from app.services.execution_service import ExecutionService
from app.services.execution_runner import execution_runner
from app.api.deps import get_job_service, get_execution_service

router = APIRouter()


@router.get("", response_model=List[JobListItemResponse])
async def list_jobs(
    server_id: int | None = Query(None, description="サーバIDでフィルタ"),
    service: JobService = Depends(get_job_service)
):
    """
    ジョブ一覧を取得
    """
    jobs_with_latest_execution = await service.get_all_with_latest_execution(
        server_id=server_id,
        include_server=True,
    )
    return [
        JobListItemResponse(
            **JobWithServerResponse.model_validate(job).model_dump(),
            latest_execution=latest_execution,
        )
        for job, latest_execution in jobs_with_latest_execution
    ]


@router.get("/{job_id}", response_model=JobWithServerResponse)
async def get_job(
    job_id: int,
    service: JobService = Depends(get_job_service)
):
    """
    ジョブ詳細を取得
    """
    try:
        job = await service.get_by_id(job_id, include_server=True)
        return job
    except JobNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    service: JobService = Depends(get_job_service)
):
    """
    ジョブを作成
    """
    try:
        job = await service.create(job_data)
        return job
    except ServerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except JobTriggerConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: int,
    job_data: JobUpdate,
    service: JobService = Depends(get_job_service)
):
    """
    ジョブを更新
    """
    try:
        job = await service.update(job_id, job_data)
        return job
    except JobNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except JobTriggerConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: int,
    service: JobService = Depends(get_job_service)
):
    """
    ジョブを削除
    """
    try:
        await service.delete(job_id)
    except JobNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{job_id}/executions", response_model=List[ExecutionResponse])
async def list_job_executions(
    job_id: int,
    limit: int = Query(50, ge=1, le=500, description="取得件数"),
    job_service: JobService = Depends(get_job_service),
    execution_service: ExecutionService = Depends(get_execution_service),
):
    """指定ジョブの実行履歴を取得する。"""

    try:
        await job_service.get_by_id(job_id)
        return await execution_service.get_by_job_id(job_id, limit=limit)
    except JobNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/{job_id}/execute", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def execute_job(
    job_id: int,
    execution_service: ExecutionService = Depends(get_execution_service)
):
    """
    ジョブを実行
    
    実行待ち履歴を作成して直ちに返し、SSH 実行はアプリ内 task で行う。
    """
    try:
        execution = await execution_service.create_pending(job_id)
        execution_runner.schedule(execution.id)
        return execution
    except JobNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

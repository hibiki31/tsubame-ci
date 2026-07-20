"""
ジョブ管理API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List

from app.schemas.job import JobCreate, JobUpdate, JobResponse
from app.schemas.execution import ExecutionResponse
from app.services.job_service import JobService, JobNotFoundError
from app.services.server_service import ServerNotFoundError
from app.services.execution_service import ExecutionService
from app.api.deps import get_job_service, get_execution_service

router = APIRouter()


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    server_id: int | None = Query(None, description="サーバIDでフィルタ"),
    service: JobService = Depends(get_job_service)
):
    """
    ジョブ一覧を取得
    """
    if server_id:
        jobs = await service.get_by_server_id(server_id)
    else:
        jobs = await service.get_all()
    return jobs


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    service: JobService = Depends(get_job_service)
):
    """
    ジョブ詳細を取得
    """
    try:
        job = await service.get_by_id(job_id)
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


@router.post("/{job_id}/execute", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def execute_job(
    job_id: int,
    execution_service: ExecutionService = Depends(get_execution_service)
):
    """
    ジョブを実行
    
    指定されたジョブを実行し、実行履歴を返す。
    実際の実行は同期的に行われる。
    """
    try:
        execution = await execution_service.create_and_execute(job_id)
        return execution
    except JobNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

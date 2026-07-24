"""
ジョブ実行履歴API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List

from app.schemas.execution import (
    ExecutionCreateRequest,
    ExecutionResponse,
    ExecutionWithJobResponse,
)
from app.services.execution_service import ExecutionService, ExecutionNotFoundError
from app.services.execution_runner import execution_runner
from app.services.job_service import JobNotFoundError
from app.api.deps import get_execution_service

router = APIRouter()


@router.get("", response_model=List[ExecutionWithJobResponse])
async def list_executions(
    limit: int = Query(100, ge=1, le=500, description="取得件数"),
    offset: int = Query(0, ge=0, description="オフセット"),
    job_id: int | None = Query(None, description="ジョブIDでフィルタ"),
    service: ExecutionService = Depends(get_execution_service)
):
    """
    実行履歴一覧を取得
    """
    if job_id:
        executions = await service.get_by_job_id(
            job_id,
            limit=limit,
            include_job=True,
        )
    else:
        executions = await service.get_all(
            limit=limit,
            offset=offset,
            include_job=True,
        )
    return executions


@router.get("/{execution_id}", response_model=ExecutionWithJobResponse)
async def get_execution(
    execution_id: int,
    service: ExecutionService = Depends(get_execution_service)
):
    """
    実行履歴詳細を取得
    """
    try:
        execution = await service.get_by_id(execution_id, include_job=True)
        return execution
    except ExecutionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post(
    "",
    response_model=ExecutionWithJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def execute_job(
    request: ExecutionCreateRequest,
    service: ExecutionService = Depends(get_execution_service)
):
    """
    ジョブを実行
    
    ジョブの実行を開始し、実行履歴を返す。
    実際の実行は非同期で行われる。
    """
    try:
        execution = await service.create_pending(request.job_id)
        execution_runner.schedule(execution.id)
        execution = await service.get_by_id(execution.id, include_job=True)
        return execution
    except JobNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{execution_id}/cancel", response_model=ExecutionResponse)
async def cancel_execution(
    execution_id: int,
    service: ExecutionService = Depends(get_execution_service)
):
    """
    実行をキャンセル
    
    現在は実装が限定的。将来的に完全なキャンセル機能を実装予定。
    """
    try:
        execution = await service.cancel_execution(execution_id)
        return execution
    except ExecutionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

"""
ジョブ実行履歴スキーマ
API リクエスト/レスポンスの型定義
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

from app.models.execution import ExecutionStatus, ExecutionTriggerSource


class ExecutionJobSummary(BaseModel):
    """実行履歴の表示に必要なジョブの要約。"""

    id: int
    name: str
    server_id: int

    model_config = ConfigDict(from_attributes=True)


# レスポンススキーマ
class ExecutionResponse(BaseModel):
    """ジョブ実行履歴のレスポンス"""
    id: int
    job_id: int
    status: ExecutionStatus
    trigger_source: ExecutionTriggerSource
    trigger_commit_sha: Optional[str] = None
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


# ジョブ情報を含むレスポンス
class ExecutionWithJobResponse(ExecutionResponse):
    """ジョブ情報を含む実行履歴レスポンス"""
    job: ExecutionJobSummary = Field(..., description="ジョブ情報")
    
    model_config = ConfigDict(from_attributes=True)


# 実行リクエスト
class ExecutionCreateRequest(BaseModel):
    """ジョブ実行リクエスト"""
    job_id: int = Field(..., gt=0, description="実行するジョブID")

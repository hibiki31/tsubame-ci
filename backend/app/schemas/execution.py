"""
ジョブ実行履歴スキーマ
API リクエスト/レスポンスの型定義
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime

from app.models.execution import (
    ExecutionKind,
    ExecutionStatus,
    ExecutionTriggerSource,
)


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
    job_id: Optional[int] = None
    execution_kind: ExecutionKind
    name_snapshot: str
    server_id_snapshot: int
    server_name_snapshot: str
    script_snapshot: str
    status: ExecutionStatus
    trigger_source: ExecutionTriggerSource
    trigger_commit_sha: Optional[str] = None
    remote_execution_id: Optional[str] = None
    remote_process_id: Optional[int] = None
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error_message: Optional[str] = None
    tracking_error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    cancel_requested_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


# ジョブ情報を含むレスポンス
class ExecutionWithJobResponse(ExecutionResponse):
    """ジョブ情報を含む実行履歴レスポンス"""
    job: Optional[ExecutionJobSummary] = Field(None, description="ジョブ情報")
    
    model_config = ConfigDict(from_attributes=True)


# 実行リクエスト
class ExecutionCreateRequest(BaseModel):
    """ジョブ実行リクエスト"""
    job_id: int = Field(..., gt=0, description="実行するジョブID")


class AdHocExecutionCreateRequest(BaseModel):
    """保存済みジョブを作らない単発実行リクエスト。"""

    name: str = Field(..., min_length=1, max_length=255, description="実行名")
    server_id: int = Field(..., gt=0, description="実行先サーバID")
    script: str = Field(..., min_length=1, description="実行するPOSIX shスクリプト")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("実行名を入力してください")
        return value

    @field_validator("script")
    @classmethod
    def validate_script(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("シェルスクリプトを入力してください")
        return value

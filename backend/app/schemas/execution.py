"""
ジョブ実行履歴スキーマ
API リクエスト/レスポンスの型定義
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

from app.models.execution import ExecutionStatus


# レスポンススキーマ
class ExecutionResponse(BaseModel):
    """ジョブ実行履歴のレスポンス"""
    id: int
    job_id: int
    status: ExecutionStatus
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
    job: dict = Field(..., description="ジョブ情報")
    
    model_config = ConfigDict(from_attributes=True)


# 実行リクエスト
class ExecutionCreateRequest(BaseModel):
    """ジョブ実行リクエスト"""
    job_id: int = Field(..., gt=0, description="実行するジョブID")


# WebSocketメッセージ
class ExecutionLogMessage(BaseModel):
    """WebSocketで送信するログメッセージ"""
    type: str = Field(..., description="メッセージタイプ: log, status, error")
    data: str = Field(..., description="メッセージデータ")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="タイムスタンプ")


class ExecutionStatusMessage(BaseModel):
    """WebSocketで送信するステータス更新メッセージ"""
    type: str = Field(default="status", description="メッセージタイプ")
    execution_id: int
    status: ExecutionStatus
    exit_code: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="タイムスタンプ")

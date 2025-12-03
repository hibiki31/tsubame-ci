"""
ジョブスキーマ
API リクエスト/レスポンスの型定義
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


# 基本スキーマ
class JobBase(BaseModel):
    """ジョブの基本情報"""
    name: str = Field(..., min_length=1, max_length=255, description="ジョブ名")
    description: Optional[str] = Field(None, max_length=500, description="ジョブの説明")
    script: str = Field(..., min_length=1, description="実行するシェルスクリプト")
    server_id: int = Field(..., gt=0, description="実行先サーバID")


# 作成時のスキーマ
class JobCreate(JobBase):
    """ジョブ作成時のリクエストボディ"""
    pass


# 更新時のスキーマ
class JobUpdate(BaseModel):
    """ジョブ更新時のリクエストボディ"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    script: Optional[str] = Field(None, min_length=1)
    server_id: Optional[int] = Field(None, gt=0)


# レスポンススキーマ
class JobResponse(JobBase):
    """ジョブ情報のレスポンス"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# サーバ情報を含むレスポンス
class JobWithServerResponse(JobResponse):
    """サーバ情報を含むジョブレスポンス"""
    server: dict = Field(..., description="サーバ情報")
    
    model_config = ConfigDict(from_attributes=True)

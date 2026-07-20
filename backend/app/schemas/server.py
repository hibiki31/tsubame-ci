"""
サーバスキーマ
API リクエスト/レスポンスの型定義
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

from app.models.server import AuthMethod, ServerConnectionStatus


# 基本スキーマ
class ServerBase(BaseModel):
    """サーバの基本情報"""
    name: str = Field(..., min_length=1, max_length=255, description="サーバ名")
    description: Optional[str] = Field(None, max_length=500, description="サーバの説明")
    host: str = Field(..., min_length=1, max_length=255, description="ホスト名またはIPアドレス")
    port: int = Field(22, ge=1, le=65535, description="SSHポート")
    username: str = Field(..., min_length=1, max_length=255, description="SSHユーザー名")
    auth_method: AuthMethod = Field(..., description="認証方式")


# 作成時のスキーマ
class ServerCreate(ServerBase):
    """サーバ作成時のリクエストボディ"""
    password: Optional[str] = Field(None, description="パスワード（auth_method=passwordの場合）")
    private_key: Optional[str] = Field(None, description="秘密鍵（auth_method=keyの場合）")


# 更新時のスキーマ
class ServerUpdate(BaseModel):
    """サーバ更新時のリクエストボディ"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    host: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, min_length=1, max_length=255)
    auth_method: Optional[AuthMethod] = None
    password: Optional[str] = Field(None, description="新しいパスワード")
    private_key: Optional[str] = Field(None, description="新しい秘密鍵")


class ServerHardwareInfo(BaseModel):
    """SSH経由で取得したハードウェア情報"""
    hostname: Optional[str] = None
    architecture: Optional[str] = None
    cpu_model: Optional[str] = None
    cpu_cores: Optional[int] = None
    memory_total_bytes: Optional[int] = None
    disk_total_bytes: Optional[int] = None


class ServerSoftwareInfo(BaseModel):
    """SSH経由で取得したソフトウェア情報"""
    os_name: Optional[str] = None
    os_version: Optional[str] = None
    kernel: Optional[str] = None
    package_manager: Optional[str] = None
    python_version: Optional[str] = None
    docker_version: Optional[str] = None
    git_version: Optional[str] = None


# レスポンススキーマ
class ServerResponse(ServerBase):
    """サーバ情報のレスポンス"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    connection_status: ServerConnectionStatus = ServerConnectionStatus.UNKNOWN
    last_checked_at: Optional[datetime] = None
    last_check_latency_ms: Optional[int] = None
    last_check_error: Optional[str] = None
    hardware_info: Optional[ServerHardwareInfo] = None
    software_info: Optional[ServerSoftwareInfo] = None
    inventory_collected_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


# SSH接続テスト用スキーマ
class ServerTestRequest(BaseModel):
    """SSH接続テストリクエスト"""
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(22, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=255)
    auth_method: AuthMethod
    password: Optional[str] = None
    private_key: Optional[str] = None


class ServerTestResponse(BaseModel):
    """SSH接続テストレスポンス"""
    success: bool
    message: str
    details: Optional[str] = None


class ServerMonitoringResponse(BaseModel):
    """定期接続監視の設定情報"""
    enabled: bool
    check_interval_seconds: int

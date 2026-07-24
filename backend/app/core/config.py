"""
アプリケーション設定
環境変数から設定を読み込む
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """アプリケーション設定クラス"""
    
    # アプリケーション設定
    app_name: str = "tsubame-ci"
    debug: bool = True
    api_version: str = "v1"
    
    # データベース設定
    database_url: str
    
    # セキュリティ設定
    secret_key: str
    encryption_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS設定
    allowed_origins: str = "http://localhost:3000"
    
    # SSH設定
    # 旧 foreground SSH 実行の互換設定。
    ssh_timeout: int = Field(default=300, ge=0)
    ssh_connect_timeout: int = 30
    ssh_keepalive_interval_seconds: int = Field(default=15, ge=0, le=300)
    ssh_keepalive_count_max: int = Field(default=3, ge=1, le=20)
    execution_ssh_operation_timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
    )
    # 0 は detached ジョブ全体の timeout 無効。
    execution_timeout_seconds: int = Field(default=0, ge=0)
    execution_poll_interval_seconds: float = Field(default=2.0, ge=0.5, le=60)
    execution_reconnect_max_interval_seconds: float = Field(
        default=30.0,
        ge=1,
        le=300,
    )
    execution_log_chunk_bytes: int = Field(
        default=65536,
        ge=4096,
        le=1048576,
    )

    # GitHub ポーリング設定
    github_polling_enabled: bool = True
    github_poll_interval_seconds: int = Field(default=60, ge=10)
    github_api_timeout_seconds: int = Field(default=10, ge=1)

    # サーバ監視設定
    server_monitor_enabled: bool = True
    server_check_interval_seconds: int = Field(300, ge=10, le=86400)
    server_check_concurrency: int = Field(5, ge=1, le=50)
    server_inventory_timeout: int = Field(15, ge=1, le=120)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )
    
    @property
    def cors_origins(self) -> List[str]:
        """CORS許可オリジンをリストとして取得"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]


# シングルトンインスタンス
settings = Settings()

"""
アプリケーション設定
環境変数から設定を読み込む
"""
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
    ssh_timeout: int = 300
    ssh_connect_timeout: int = 30
    
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

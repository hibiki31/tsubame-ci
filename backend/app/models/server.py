"""
サーバモデル
SSH接続先サーバの情報を管理
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class AuthMethod(str, enum.Enum):
    """SSH認証方式"""
    PASSWORD = "password"
    KEY = "key"


class ServerConnectionStatus(str, enum.Enum):
    """サーバ接続状態"""
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"


class Server(Base):
    """
    サーバテーブル
    SSH接続先のサーバ情報を保存
    """
    __tablename__ = "servers"
    
    # 基本情報
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="サーバ名（表示用）")
    description = Column(String(500), nullable=True, comment="サーバの説明")
    
    # 接続情報
    host = Column(String(255), nullable=False, comment="ホスト名またはIPアドレス")
    port = Column(Integer, default=22, nullable=False, comment="SSHポート")
    username = Column(String(255), nullable=False, comment="SSHユーザー名")
    
    # 認証情報（暗号化して保存）
    auth_method = Column(
        SQLEnum(AuthMethod),
        nullable=False,
        default=AuthMethod.PASSWORD,
        comment="認証方式"
    )
    password_encrypted = Column(String(500), nullable=True, comment="暗号化されたパスワード")
    private_key_encrypted = Column(String(5000), nullable=True, comment="暗号化された秘密鍵")

    # 監視情報
    connection_status = Column(
        String(20),
        nullable=False,
        default=ServerConnectionStatus.UNKNOWN.value,
        server_default=ServerConnectionStatus.UNKNOWN.value,
        index=True,
        comment="直近のSSH接続状態"
    )
    last_checked_at = Column(DateTime(timezone=True), nullable=True, comment="最終接続確認日時")
    last_check_latency_ms = Column(Integer, nullable=True, comment="SSH接続時間（ミリ秒）")
    last_check_error = Column(Text, nullable=True, comment="直近の接続確認または構成取得エラー")
    hardware_info = Column(JSON, nullable=True, comment="直近に取得したハードウェア情報")
    software_info = Column(JSON, nullable=True, comment="直近に取得したソフトウェア情報")
    inventory_collected_at = Column(DateTime(timezone=True), nullable=True, comment="構成情報取得日時")
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="作成日時")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新日時")
    
    # リレーション
    jobs = relationship("Job", back_populates="server", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Server(id={self.id}, name={self.name}, host={self.host})>"

"""
サーバモデル
SSH接続先サーバの情報を管理
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class AuthMethod(str, enum.Enum):
    """SSH認証方式"""
    PASSWORD = "password"
    KEY = "key"


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
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="作成日時")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新日時")
    
    # リレーション
    jobs = relationship("Job", back_populates="server", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Server(id={self.id}, name={self.name}, host={self.host})>"

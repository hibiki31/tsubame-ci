"""
ジョブモデル
実行するジョブの定義を管理
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Job(Base):
    """
    ジョブテーブル
    実行するジョブ（スクリプト）の定義を保存
    """
    __tablename__ = "jobs"
    
    # 基本情報
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True, comment="ジョブ名")
    description = Column(String(500), nullable=True, comment="ジョブの説明")
    
    # スクリプト情報
    script = Column(Text, nullable=False, comment="実行するシェルスクリプト")
    
    # 実行先サーバ
    server_id = Column(
        Integer,
        ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="実行先サーバID"
    )
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="作成日時")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新日時")
    
    # リレーション
    server = relationship("Server", back_populates="jobs")
    executions = relationship("JobExecution", back_populates="job", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Job(id={self.id}, name={self.name}, server_id={self.server_id})>"

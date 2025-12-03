"""
ジョブ実行履歴モデル
ジョブの実行結果とログを管理
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class ExecutionStatus(str, enum.Enum):
    """実行ステータス"""
    PENDING = "pending"      # 実行待ち
    RUNNING = "running"      # 実行中
    SUCCESS = "success"      # 成功
    FAILED = "failed"        # 失敗
    TIMEOUT = "timeout"      # タイムアウト
    CANCELLED = "cancelled"  # キャンセル


class JobExecution(Base):
    """
    ジョブ実行履歴テーブル
    各ジョブの実行結果とログを保存
    """
    __tablename__ = "job_executions"
    
    # 基本情報
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(
        Integer,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ジョブID"
    )
    
    # 実行状態
    status = Column(
        SQLEnum(ExecutionStatus),
        nullable=False,
        default=ExecutionStatus.PENDING,
        index=True,
        comment="実行ステータス"
    )
    
    # 実行結果
    exit_code = Column(Integer, nullable=True, comment="終了コード")
    stdout = Column(Text, nullable=True, comment="標準出力")
    stderr = Column(Text, nullable=True, comment="標準エラー出力")
    error_message = Column(Text, nullable=True, comment="エラーメッセージ")
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="作成日時")
    started_at = Column(DateTime(timezone=True), nullable=True, comment="実行開始日時")
    finished_at = Column(DateTime(timezone=True), nullable=True, comment="実行終了日時")
    
    # リレーション
    job = relationship("Job", back_populates="executions")
    
    def __repr__(self):
        return f"<JobExecution(id={self.id}, job_id={self.job_id}, status={self.status})>"
    
    @property
    def duration_seconds(self) -> float | None:
        """実行時間を秒で取得"""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

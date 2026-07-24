"""
ジョブ実行履歴モデル
ジョブの実行結果とログを管理
"""
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
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


class ExecutionTriggerSource(str, enum.Enum):
    """実行を開始した契機"""

    MANUAL = "manual"
    GITHUB_POLL = "github_poll"


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
    trigger_source = Column(
        SQLEnum(ExecutionTriggerSource),
        nullable=False,
        default=ExecutionTriggerSource.MANUAL,
        server_default="MANUAL",
        comment="実行契機",
    )
    trigger_commit_sha = Column(String(40), nullable=True, comment="実行契機となったcommit SHA")

    # 実行開始後に Job が変更されても、同じ対象と script を再追跡するための snapshot
    server_id_snapshot = Column(Integer, nullable=False, comment="実行開始時のサーバID")
    script_snapshot = Column(Text, nullable=False, comment="実行開始時のスクリプト")

    # SSH session から分離したリモート実行の追跡情報
    remote_execution_id = Column(
        String(32),
        nullable=True,
        unique=True,
        index=True,
        comment="対象サーバ上の一意な実行ID",
    )
    remote_process_id = Column(Integer, nullable=True, comment="リモートrunnerのPID")
    stdout_offset = Column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="同期済みstdout byte数",
    )
    stderr_offset = Column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="同期済みstderr byte数",
    )
    last_synced_at = Column(DateTime(timezone=True), nullable=True, comment="最終追跡成功日時")
    tracking_error = Column(Text, nullable=True, comment="直近の一時的な追跡エラー")
    cancel_requested_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="キャンセル要求日時",
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

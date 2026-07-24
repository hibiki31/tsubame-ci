"""
ジョブモデル
実行するジョブの定義を管理
"""
import enum

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class JobTriggerType(str, enum.Enum):
    """ジョブの自動実行トリガー"""

    MANUAL = "manual"
    GITHUB_POLL = "github_poll"


class GitHubTokenSource(str, enum.Enum):
    """GitHub API へ使用する認証情報の取得元。"""

    NONE = "none"
    SHARED = "shared"
    JOB = "job"


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

    # GitHub ブランチポーリングトリガー
    trigger_type = Column(
        SQLEnum(JobTriggerType),
        nullable=False,
        default=JobTriggerType.MANUAL,
        server_default="MANUAL",
        index=True,
        comment="ジョブトリガー種別",
    )
    github_repository = Column(String(255), nullable=True, comment="GitHub owner/repository")
    github_branch = Column(String(255), nullable=True, comment="監視対象ブランチ")
    github_token_source = Column(
        SQLEnum(GitHubTokenSource),
        nullable=False,
        default=GitHubTokenSource.NONE,
        server_default="NONE",
        comment="GitHub PATの取得元",
    )
    github_token_encrypted = Column(String(2000), nullable=True, comment="暗号化済みGitHub PAT")
    github_last_commit_sha = Column(String(40), nullable=True, comment="最後に確認したcommit SHA")
    github_etag = Column(String(255), nullable=True, comment="GitHub API ETag")
    github_last_checked_at = Column(DateTime(timezone=True), nullable=True, comment="最終確認日時")
    github_last_error = Column(Text, nullable=True, comment="最終ポーリングエラー")
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="作成日時")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新日時")
    
    # リレーション
    server = relationship("Server", back_populates="jobs")
    executions = relationship("JobExecution", back_populates="job", cascade="all, delete-orphan")

    @property
    def github_token_configured(self) -> bool:
        """GitHub PAT が設定済みかを、値を露出せず返す。"""

        return bool(self.github_token_encrypted)
    
    def __repr__(self):
        return f"<Job(id={self.id}, name={self.name}, server_id={self.server_id})>"

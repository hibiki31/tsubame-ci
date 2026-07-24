"""ジョブ間で共有する GitHub PAT の保存モデル。"""

from sqlalchemy import CheckConstraint, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class GitHubToken(Base):
    """アプリ全体で共有する write-only の GitHub PAT。"""

    __tablename__ = "github_tokens"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_github_tokens_singleton"),
    )

    id = Column(Integer, primary_key=True, default=1)
    token_encrypted = Column(
        String(2000),
        nullable=False,
        comment="暗号化済み共有GitHub PAT",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="作成日時",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新日時",
    )

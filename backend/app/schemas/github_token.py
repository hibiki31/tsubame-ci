"""共有 GitHub PAT API の入出力スキーマ。"""

from datetime import datetime

from pydantic import BaseModel, Field


class GitHubTokenUpdate(BaseModel):
    """共有 GitHub PAT の登録・更新入力。"""

    token: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="共有GitHub PAT（write-only）",
    )


class GitHubTokenResponse(BaseModel):
    """共有 GitHub PAT の安全な設定状態。"""

    configured: bool
    updated_at: datetime | None = None

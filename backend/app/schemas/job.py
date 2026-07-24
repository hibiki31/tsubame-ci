"""ジョブ API の入出力スキーマ。"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.execution import ExecutionStatus
from app.models.job import GitHubTokenSource, JobTriggerType
from app.schemas.server import ServerResponse


GITHUB_REPOSITORY_PATTERN = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}$"
)


class JobFields(BaseModel):
    """ジョブ定義の共通フィールド。"""

    name: str = Field(..., min_length=1, max_length=255, description="ジョブ名")
    description: Optional[str] = Field(None, max_length=500, description="ジョブの説明")
    script: str = Field(..., min_length=1, description="実行するシェルスクリプト")
    server_id: int = Field(..., gt=0, description="実行先サーバID")


class GitHubTriggerInput(BaseModel):
    """GitHub ポーリング設定の入力フィールド。"""

    trigger_type: JobTriggerType = JobTriggerType.MANUAL
    github_repository: Optional[str] = Field(
        None,
        max_length=255,
        description="監視する GitHub repository（owner/repository）",
    )
    github_branch: Optional[str] = Field(None, min_length=1, max_length=255)
    github_token_source: GitHubTokenSource = GitHubTokenSource.NONE
    github_token: Optional[str] = Field(
        None,
        min_length=1,
        max_length=1000,
        description="GitHub PAT（write-only）",
    )

    @field_validator("github_repository")
    @classmethod
    def validate_repository(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not GITHUB_REPOSITORY_PATTERN.fullmatch(value):
            raise ValueError("GitHubリポジトリは owner/repository 形式で指定してください")
        return value

    @field_validator("github_branch")
    @classmethod
    def normalize_branch(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("監視対象ブランチを指定してください")
        if any(character.isspace() for character in value):
            raise ValueError("ブランチ名に空白は使用できません")
        return value


class JobCreate(JobFields, GitHubTriggerInput):
    """ジョブ作成リクエスト。"""

    @model_validator(mode="after")
    def validate_github_trigger(self) -> "JobCreate":
        if self.trigger_type == JobTriggerType.GITHUB_POLL:
            if not self.github_repository or not self.github_branch:
                raise ValueError("GitHubトリガーにはリポジトリとブランチが必要です")
            if (
                self.github_token
                and self.github_token_source == GitHubTokenSource.NONE
            ):
                # github_token_source 導入前の client との互換性を維持する。
                self.github_token_source = GitHubTokenSource.JOB
            if (
                self.github_token_source == GitHubTokenSource.JOB
                and not self.github_token
            ):
                raise ValueError("ジョブ固有トークンを入力してください")
            if (
                self.github_token_source != GitHubTokenSource.JOB
                and self.github_token
            ):
                raise ValueError(
                    "GitHubトークンはジョブ固有トークン選択時だけ指定できます"
                )
        return self


class JobUpdate(BaseModel):
    """ジョブ更新リクエスト。未指定フィールドは現在値を維持する。"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    script: Optional[str] = Field(None, min_length=1)
    server_id: Optional[int] = Field(None, gt=0)
    trigger_type: Optional[JobTriggerType] = None
    github_repository: Optional[str] = Field(None, max_length=255)
    github_branch: Optional[str] = Field(None, min_length=1, max_length=255)
    github_token_source: Optional[GitHubTokenSource] = None
    github_token: Optional[str] = Field(None, min_length=1, max_length=1000)

    _validate_repository = field_validator("github_repository")(
        GitHubTriggerInput.validate_repository.__func__
    )
    _normalize_branch = field_validator("github_branch")(
        GitHubTriggerInput.normalize_branch.__func__
    )

    @model_validator(mode="after")
    def normalize_token_source(self) -> "JobUpdate":
        if self.github_token and self.github_token_source is None:
            # github_token_source 導入前の client との互換性を維持する。
            self.github_token_source = GitHubTokenSource.JOB
        if (
            self.github_token
            and self.github_token_source != GitHubTokenSource.JOB
        ):
            raise ValueError(
                "GitHubトークンはジョブ固有トークン選択時だけ指定できます"
            )
        return self


class JobResponse(JobFields):
    """認証情報を含まないジョブレスポンス。"""

    id: int
    trigger_type: JobTriggerType
    github_repository: Optional[str] = None
    github_branch: Optional[str] = None
    github_token_source: GitHubTokenSource
    github_token_configured: bool
    github_last_commit_sha: Optional[str] = None
    github_last_checked_at: Optional[datetime] = None
    github_last_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobWithServerResponse(JobResponse):
    """サーバ情報を含むジョブレスポンス。"""

    server: ServerResponse

    model_config = ConfigDict(from_attributes=True)


class JobLatestExecutionResponse(BaseModel):
    """ジョブ一覧に表示する最新実行の要約。"""

    id: int
    status: ExecutionStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobListItemResponse(JobWithServerResponse):
    """最新実行を含むジョブ一覧レスポンス。"""

    latest_execution: Optional[JobLatestExecutionResponse] = None

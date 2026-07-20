"""GitHub branch API client。PAT は Authorization header 以外へ出力しない。"""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import httpx

from app.core.config import settings


class GitHubAPIError(Exception):
    """GitHub API の確認に失敗した。"""


@dataclass(frozen=True)
class GitHubBranchResult:
    """branch HEAD の取得結果。"""

    sha: Optional[str]
    etag: Optional[str]
    not_modified: bool = False


class GitHubService:
    """GitHub REST API から branch HEAD を取得する。"""

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url="https://api.github.com",
            timeout=settings.github_api_timeout_seconds,
        )

    async def get_branch_head(
        self,
        repository: str,
        branch: str,
        token: str | None = None,
        etag: str | None = None,
    ) -> GitHubBranchResult:
        owner, repository_name = repository.split("/", 1)
        path = "/repos/{owner}/{repository}/branches/{branch}".format(
            owner=quote(owner, safe=""),
            repository=quote(repository_name, safe=""),
            branch=quote(branch, safe=""),
        )
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "tsubame-ci",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if etag:
            headers["If-None-Match"] = etag

        try:
            response = await self._client.get(path, headers=headers)
        except httpx.TimeoutException as error:
            raise GitHubAPIError("GitHub APIへの接続がタイムアウトしました") from error
        except httpx.RequestError as error:
            raise GitHubAPIError("GitHub APIへ接続できませんでした") from error

        response_etag = response.headers.get("ETag") or etag
        if response.status_code == httpx.codes.NOT_MODIFIED:
            return GitHubBranchResult(
                sha=None,
                etag=response_etag,
                not_modified=True,
            )
        if response.status_code == httpx.codes.UNAUTHORIZED:
            raise GitHubAPIError("GitHubトークンが無効です")
        if response.status_code == httpx.codes.FORBIDDEN:
            if response.headers.get("X-RateLimit-Remaining") == "0":
                raise GitHubAPIError("GitHub APIのレート制限に達しました")
            raise GitHubAPIError("GitHubトークンにリポジトリの読み取り権限がありません")
        if response.status_code == httpx.codes.NOT_FOUND:
            raise GitHubAPIError(
                "リポジトリまたはブランチが見つかりません。"
                "private repositoryではContentsの読み取り権限を持つトークンが必要です"
            )
        if response.is_error:
            raise GitHubAPIError(
                f"GitHub APIがエラーを返しました（HTTP {response.status_code}）"
            )

        try:
            sha = response.json()["commit"]["sha"]
        except (KeyError, TypeError, ValueError) as error:
            raise GitHubAPIError("GitHub APIの応答からcommit SHAを取得できませんでした") from error
        if not isinstance(sha, str) or len(sha) != 40:
            raise GitHubAPIError("GitHub APIが不正なcommit SHAを返しました")

        return GitHubBranchResult(sha=sha, etag=response_etag)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

"""ジョブ間で共有する GitHub PAT を管理する。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import credential_encryptor
from app.models.github_token import GitHubToken
from app.models.job import GitHubTokenSource, Job


class GitHubTokenInUseError(Exception):
    """共有 GitHub PAT を参照するジョブが存在する。"""


class GitHubTokenService:
    """共有 GitHub PAT の取得・登録・削除サービス。"""

    TOKEN_ID = 1

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, *, for_update: bool = False) -> GitHubToken | None:
        query = select(GitHubToken).where(GitHubToken.id == self.TOKEN_ID)
        if for_update:
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def upsert(self, plaintext_token: str) -> GitHubToken:
        token = await self.get(for_update=True)
        encrypted_token = credential_encryptor.encrypt(plaintext_token)
        if token:
            token.token_encrypted = encrypted_token
        else:
            token = GitHubToken(
                id=self.TOKEN_ID,
                token_encrypted=encrypted_token,
            )
            self.db.add(token)

        await self.db.commit()
        await self.db.refresh(token)
        return token

    async def delete(self) -> None:
        token = await self.get(for_update=True)
        if not token:
            return

        result = await self.db.execute(
            select(func.count(Job.id)).where(
                Job.github_token_source == GitHubTokenSource.SHARED
            )
        )
        shared_job_count = result.scalar_one()
        if shared_job_count:
            raise GitHubTokenInUseError(
                f"共通トークンを使用するジョブが{shared_job_count}件あります"
            )

        await self.db.delete(token)
        await self.db.commit()

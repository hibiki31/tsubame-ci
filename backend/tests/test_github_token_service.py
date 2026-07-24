import unittest
from unittest.mock import AsyncMock, Mock

from app.core.security import credential_encryptor
from app.models.github_token import GitHubToken
from app.services.github_token_service import (
    GitHubTokenInUseError,
    GitHubTokenService,
)


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class GitHubTokenServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_upsert_encrypts_token_before_persistence(self) -> None:
        db = AsyncMock()
        db.add = Mock()
        service = GitHubTokenService(db)
        service.get = AsyncMock(return_value=None)

        token = await service.upsert("github-plain-token")

        self.assertNotEqual(token.token_encrypted, "github-plain-token")
        self.assertEqual(
            credential_encryptor.decrypt(token.token_encrypted),
            "github-plain-token",
        )
        db.add.assert_called_once_with(token)
        db.commit.assert_awaited_once_with()

    async def test_delete_rejects_token_used_by_jobs(self) -> None:
        db = AsyncMock()
        db.execute.return_value = FakeScalarResult(2)
        service = GitHubTokenService(db)
        service.get = AsyncMock(
            return_value=GitHubToken(id=1, token_encrypted="encrypted")
        )

        with self.assertRaises(GitHubTokenInUseError):
            await service.delete()

        db.delete.assert_not_awaited()

    async def test_delete_is_idempotent_when_not_configured(self) -> None:
        db = AsyncMock()
        service = GitHubTokenService(db)
        service.get = AsyncMock(return_value=None)

        await service.delete()

        db.delete.assert_not_awaited()
        db.commit.assert_not_awaited()

    async def test_delete_removes_unreferenced_token(self) -> None:
        db = AsyncMock()
        db.execute.return_value = FakeScalarResult(0)
        service = GitHubTokenService(db)
        token = GitHubToken(id=1, token_encrypted="encrypted")
        service.get = AsyncMock(return_value=token)

        await service.delete()

        db.delete.assert_awaited_once_with(token)
        db.commit.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()

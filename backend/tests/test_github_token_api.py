import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import HTTPException

from app.api.v1.github_token import (
    delete_github_token,
    get_github_token,
    update_github_token,
)
from app.schemas.github_token import GitHubTokenUpdate
from app.services.github_token_service import GitHubTokenInUseError


class GitHubTokenApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_exposes_status_without_token_value(self) -> None:
        updated_at = datetime.now(timezone.utc)
        service = AsyncMock()
        service.get.return_value = SimpleNamespace(updated_at=updated_at)

        response = await get_github_token(service=service)

        self.assertTrue(response.configured)
        self.assertEqual(response.updated_at, updated_at)
        self.assertNotIn("token", response.model_dump())

    async def test_update_passes_plaintext_only_to_service(self) -> None:
        updated_at = datetime.now(timezone.utc)
        service = AsyncMock()
        service.upsert.return_value = SimpleNamespace(updated_at=updated_at)

        response = await update_github_token(
            GitHubTokenUpdate(token="github-secret"),
            service=service,
        )

        self.assertTrue(response.configured)
        service.upsert.assert_awaited_once_with("github-secret")

    async def test_delete_maps_in_use_error_to_conflict(self) -> None:
        service = AsyncMock()
        service.delete.side_effect = GitHubTokenInUseError(
            "共通トークンを使用するジョブが1件あります"
        )

        with self.assertRaises(HTTPException) as raised:
            await delete_github_token(service=service)

        self.assertEqual(raised.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()

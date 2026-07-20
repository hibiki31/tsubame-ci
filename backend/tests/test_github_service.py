import unittest

import httpx

from app.services.github_service import GitHubAPIError, GitHubService


class GitHubServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_private_repository_request_uses_bearer_token(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers["Authorization"], "Bearer github-secret")
            self.assertEqual(request.headers["If-None-Match"], '"old-etag"')
            self.assertEqual(
                request.url.raw_path,
                b"/repos/acme/private-project/branches/release%2Fv1",
            )
            return httpx.Response(
                200,
                headers={"ETag": '"new-etag"'},
                json={"commit": {"sha": "a" * 40}},
            )

        async with httpx.AsyncClient(
            base_url="https://api.github.test",
            transport=httpx.MockTransport(handler),
        ) as client:
            result = await GitHubService(client).get_branch_head(
                repository="acme/private-project",
                branch="release/v1",
                token="github-secret",
                etag='"old-etag"',
            )

        self.assertEqual(result.sha, "a" * 40)
        self.assertEqual(result.etag, '"new-etag"')
        self.assertFalse(result.not_modified)

    async def test_not_modified_response_does_not_require_sha(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(304, headers={"ETag": '"same"'})
        )
        async with httpx.AsyncClient(
            base_url="https://api.github.test",
            transport=transport,
        ) as client:
            result = await GitHubService(client).get_branch_head(
                repository="acme/project",
                branch="main",
                etag='"same"',
            )

        self.assertTrue(result.not_modified)
        self.assertIsNone(result.sha)

    async def test_authentication_error_does_not_expose_token(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(401, json={"message": "Bad credentials"})
        )
        async with httpx.AsyncClient(
            base_url="https://api.github.test",
            transport=transport,
        ) as client:
            with self.assertRaises(GitHubAPIError) as raised:
                await GitHubService(client).get_branch_head(
                    repository="acme/private-project",
                    branch="main",
                    token="never-show-this-token",
                )

        self.assertEqual(str(raised.exception), "GitHubトークンが無効です")
        self.assertNotIn("never-show-this-token", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

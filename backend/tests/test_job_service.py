import unittest
from unittest.mock import AsyncMock, Mock

from app.core.security import credential_encryptor
from app.models.job import JobTriggerType
from app.schemas.job import JobCreate
from app.services.job_service import JobService


class JobServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_create_encrypts_github_token_before_persistence(self) -> None:
        db = AsyncMock()
        db.add = Mock()
        service = JobService(db)
        service.server_service.get_by_id = AsyncMock()
        request = JobCreate(
            name="deploy",
            script="./deploy.sh",
            server_id=1,
            trigger_type=JobTriggerType.GITHUB_POLL,
            github_repository="acme/private-project",
            github_branch="main",
            github_token="github-plain-token",
        )

        job = await service.create(request)

        self.assertNotEqual(job.github_token_encrypted, "github-plain-token")
        self.assertEqual(
            credential_encryptor.decrypt(job.github_token_encrypted),
            "github-plain-token",
        )
        self.assertTrue(job.github_token_configured)
        db.add.assert_called_once_with(job)
        db.commit.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()

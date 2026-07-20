import unittest

from pydantic import ValidationError

from app.models.job import JobTriggerType
from app.schemas.job import JobCreate, JobUpdate


class JobSchemaTest(unittest.TestCase):
    def base_job(self) -> dict:
        return {
            "name": "deploy",
            "description": "deploy application",
            "script": "./deploy.sh",
            "server_id": 1,
        }

    def test_github_trigger_requires_repository_and_branch(self) -> None:
        with self.assertRaises(ValidationError):
            JobCreate(
                **self.base_job(),
                trigger_type=JobTriggerType.GITHUB_POLL,
            )

    def test_github_repository_and_branch_are_normalized(self) -> None:
        job = JobCreate(
            **self.base_job(),
            trigger_type=JobTriggerType.GITHUB_POLL,
            github_repository=" acme/private-project ",
            github_branch=" release/v1 ",
            github_token="secret",
        )

        self.assertEqual(job.github_repository, "acme/private-project")
        self.assertEqual(job.github_branch, "release/v1")

    def test_update_rejects_invalid_repository_format(self) -> None:
        with self.assertRaises(ValidationError):
            JobUpdate(github_repository="https://github.com/acme/project")


if __name__ == "__main__":
    unittest.main()

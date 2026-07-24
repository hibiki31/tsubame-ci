import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from app.models.execution import ExecutionStatus, ExecutionTriggerSource
from app.schemas.execution import ExecutionWithJobResponse


class ExecutionSchemaTest(unittest.TestCase):
    def test_execution_with_job_accepts_nested_orm_attributes(self) -> None:
        execution = SimpleNamespace(
            id=1,
            job_id=2,
            status=ExecutionStatus.RUNNING,
            trigger_source=ExecutionTriggerSource.MANUAL,
            trigger_commit_sha=None,
            exit_code=None,
            stdout="deploying\n",
            stderr=None,
            error_message=None,
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            finished_at=None,
            duration_seconds=None,
            job=SimpleNamespace(id=2, name="deploy", server_id=3),
        )

        response = ExecutionWithJobResponse.model_validate(execution)

        self.assertEqual(response.job.name, "deploy")
        self.assertEqual(response.job.server_id, 3)
        self.assertEqual(response.stdout, "deploying\n")


if __name__ == "__main__":
    unittest.main()

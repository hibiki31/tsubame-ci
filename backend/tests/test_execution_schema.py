import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from pydantic import ValidationError

from app.models.execution import (
    ExecutionKind,
    ExecutionStatus,
    ExecutionTriggerSource,
)
from app.schemas.execution import (
    AdHocExecutionCreateRequest,
    ExecutionWithJobResponse,
)


class ExecutionSchemaTest(unittest.TestCase):
    def test_execution_with_job_accepts_nested_orm_attributes(self) -> None:
        execution = SimpleNamespace(
            id=1,
            job_id=2,
            execution_kind=ExecutionKind.JOB,
            name_snapshot="deploy",
            server_id_snapshot=3,
            server_name_snapshot="production",
            script_snapshot="./deploy.sh",
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

    def test_execution_with_job_exposes_trigger_and_job_name(self) -> None:
        response = ExecutionWithJobResponse.model_validate(
            {
                "id": 12,
                "job_id": 3,
                "execution_kind": ExecutionKind.JOB,
                "name_snapshot": "本番デプロイ",
                "server_id_snapshot": 8,
                "server_name_snapshot": "production",
                "script_snapshot": "./deploy.sh",
                "status": ExecutionStatus.SUCCESS,
                "trigger_source": ExecutionTriggerSource.GITHUB_POLL,
                "trigger_commit_sha": "a" * 40,
                "created_at": datetime.now(timezone.utc),
                "job": {
                    "id": 3,
                    "name": "本番デプロイ",
                    "server_id": 8,
                },
            }
        )

        self.assertEqual(response.trigger_source, ExecutionTriggerSource.GITHUB_POLL)
        self.assertEqual(response.job.name, "本番デプロイ")

    def test_ad_hoc_execution_accepts_missing_job(self) -> None:
        response = ExecutionWithJobResponse.model_validate(
            {
                "id": 13,
                "job_id": None,
                "execution_kind": ExecutionKind.AD_HOC,
                "name_snapshot": "月次集計",
                "server_id_snapshot": 8,
                "server_name_snapshot": "batch-server",
                "script_snapshot": "./monthly.sh",
                "status": ExecutionStatus.PENDING,
                "trigger_source": ExecutionTriggerSource.MANUAL,
                "created_at": datetime.now(timezone.utc),
                "job": None,
            }
        )

        self.assertIsNone(response.job_id)
        self.assertIsNone(response.job)
        self.assertEqual(response.execution_kind, ExecutionKind.AD_HOC)

    def test_ad_hoc_request_rejects_whitespace_only_script(self) -> None:
        with self.assertRaises(ValidationError):
            AdHocExecutionCreateRequest(
                name="月次集計",
                server_id=8,
                script=" \n ",
            )


if __name__ == "__main__":
    unittest.main()

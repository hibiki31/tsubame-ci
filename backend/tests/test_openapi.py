import unittest

from app.main import app


class OpenAPITest(unittest.TestCase):
    def test_execution_detail_uses_nested_job_response(self) -> None:
        schema = app.openapi()
        response_schema = schema["paths"][
            "/api/v1/executions/{execution_id}"
        ]["get"]["responses"]["200"]["content"]["application/json"]["schema"]

        self.assertEqual(
            response_schema["$ref"],
            "#/components/schemas/ExecutionWithJobResponse",
        )

    def test_execution_response_exposes_remote_tracking_state(self) -> None:
        properties = app.openapi()["components"]["schemas"][
            "ExecutionResponse"
        ]["properties"]

        self.assertIn("remote_execution_id", properties)
        self.assertIn("remote_process_id", properties)
        self.assertIn("last_synced_at", properties)
        self.assertIn("tracking_error", properties)
        self.assertIn("cancel_requested_at", properties)

    def test_shared_github_token_response_never_exposes_token_value(self) -> None:
        schema = app.openapi()
        properties = schema["components"]["schemas"][
            "GitHubTokenResponse"
        ]["properties"]

        self.assertIn("/api/v1/github-token", schema["paths"])
        self.assertEqual(set(properties), {"configured", "updated_at"})

    def test_job_response_exposes_token_source_not_token_value(self) -> None:
        properties = app.openapi()["components"]["schemas"][
            "JobResponse"
        ]["properties"]

        self.assertIn("github_token_source", properties)
        self.assertNotIn("github_token", properties)


if __name__ == "__main__":
    unittest.main()

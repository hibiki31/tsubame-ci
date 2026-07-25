import unittest

from app.main import app


class OpenAPITest(unittest.TestCase):
    def test_job_list_exposes_latest_execution_summary(self) -> None:
        schema = app.openapi()
        response_items = schema["paths"]["/api/v1/jobs"]["get"]["responses"][
            "200"
        ]["content"]["application/json"]["schema"]["items"]
        properties = schema["components"]["schemas"][
            "JobLatestExecutionResponse"
        ]["properties"]

        self.assertEqual(
            response_items["$ref"],
            "#/components/schemas/JobListItemResponse",
        )
        self.assertEqual(
            set(properties),
            {"id", "status", "created_at"},
        )

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

    def test_ad_hoc_execution_has_dedicated_create_contract(self) -> None:
        schema = app.openapi()
        operation = schema["paths"]["/api/v1/executions/ad-hoc"]["post"]
        request_schema = operation["requestBody"]["content"][
            "application/json"
        ]["schema"]
        properties = schema["components"]["schemas"][
            "ExecutionResponse"
        ]["properties"]

        self.assertEqual(
            request_schema["$ref"],
            "#/components/schemas/AdHocExecutionCreateRequest",
        )
        self.assertIn("execution_kind", properties)
        self.assertIn("name_snapshot", properties)
        self.assertIn("server_name_snapshot", properties)
        self.assertIn("script_snapshot", properties)

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

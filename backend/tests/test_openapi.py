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


if __name__ == "__main__":
    unittest.main()

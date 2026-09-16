import unittest

from fastapi.testclient import TestClient

from week1.app import create_app


class Week1PolicyQaTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())

    def test_supported_question_runs_langgraph_evidence_workflow(self):
        response = self.client.post(
            "/query", json={"question": "휴가 신청은 며칠 전에 해야 하나요?"}
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "answered")
        self.assertEqual(body["difficulty"], 1)
        self.assertEqual(body["business_use_case"], "hr_leave_policy_self_service")
        self.assertEqual(body["workflow_engine"], "langgraph")
        self.assertEqual(
            body["agents_run"], ["retriever", "answer", "evidence_guard"]
        )
        self.assertEqual(body["citations"][0]["document_id"], "leave-policy")


if __name__ == "__main__":
    unittest.main()

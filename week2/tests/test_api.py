import unittest

from fastapi.testclient import TestClient

from week2.app import create_app


class Week2ExpenseReviewTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())

    def test_missing_receipt_routes_langgraph_state_to_clarify(self):
        response = self.client.post(
            "/review",
            json={"amount": 120000, "receipt_attached": False, "purpose": "client_meeting"},
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["difficulty"], 2)
        self.assertEqual(body["business_use_case"], "expense_claim_precheck")
        self.assertEqual(body["workflow_engine"], "langgraph")
        self.assertEqual(body["status"], "clarify")
        self.assertEqual(
            body["agents_run"],
            ["policy_retriever", "evidence_extractor", "policy_reviewer", "risk_router"],
        )
        self.assertEqual(body["required_follow_up"], "receipt_required")
        self.assertEqual(body["citations"][0]["document_id"], "expense-policy")


if __name__ == "__main__":
    unittest.main()

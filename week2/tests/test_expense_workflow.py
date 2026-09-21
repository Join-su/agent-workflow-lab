import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from week2.app import (
    ExpenseClassification,
    ExpenseRequest,
    classify_expense_fixture,
    create_app,
    run_expense_review,
)


class Week2ExpenseWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())

    def claim(self, **overrides):
        payload = {"amount": 35_000, "receipt_attached": True, "purpose": "고객 미팅 교통비"}
        payload.update(overrides)
        return ExpenseRequest(**payload)

    def test_claim_is_classified_into_a_closed_value_set(self):
        classification = classify_expense_fixture(self.claim())

        self.assertIsInstance(classification, ExpenseClassification)
        self.assertEqual(classification.category, "transport")
        self.assertEqual(classification.priority, "normal")
        self.assertTrue(classification.reason)

    def test_out_of_schema_category_is_rejected_instead_of_defaulting(self):
        with self.assertRaises(ValueError):
            ExpenseClassification(category="entertainment", priority="normal", reason="x")

    def test_retrieval_is_filtered_to_the_classified_category(self):
        lodging = run_expense_review(self.claim(purpose="부산 채용 설명회 숙박비"))
        transport = run_expense_review(self.claim(purpose="서울 고객사 교통비"))

        self.assertEqual(lodging["category"], "lodging")
        self.assertTrue(
            all("lodging" in item["document_id"] for item in lodging["citations"])
        )
        self.assertEqual(transport["category"], "transport")
        self.assertTrue(
            all("transport" in item["document_id"] for item in transport["citations"])
        )
        self.assertNotEqual(lodging["citations"], transport["citations"])

    def test_classification_runs_before_retrieval_in_the_graph(self):
        result = run_expense_review(self.claim())

        self.assertEqual(result["agents_run"][0], "classifier")
        self.assertEqual(result["agents_run"][1], "policy_retriever")

    def test_missing_receipt_is_a_deterministic_rule_not_a_model_judgement(self):
        result = run_expense_review(self.claim(receipt_attached=False))

        self.assertEqual(result["status"], "clarify")
        self.assertEqual(result["required_follow_up"], "receipt_required")

    def test_urgent_priority_takes_the_manager_review_branch(self):
        result = run_expense_review(self.claim(amount=600_000, purpose="긴급 교통비 정산"))

        self.assertEqual(result["priority"], "urgent")
        self.assertEqual(result["status"], "manager_review")
        self.assertEqual(result["required_follow_up"], "manager_approval_required")
        self.assertIn("manager_review", result["agents_run"])

    def test_normal_claim_with_evidence_is_approved_for_the_next_step(self):
        result = run_expense_review(self.claim())

        self.assertEqual(result["difficulty"], 2)
        self.assertEqual(result["mode"], "fixture")
        self.assertEqual(result["status"], "approved_for_next_step")
        self.assertTrue(result["citations"])

    def test_empty_category_retrieval_closes_without_summarizing(self):
        def fail_if_called(*args, **kwargs):
            self.fail("reviewer must not summarize without retrieved policy evidence")

        with (
            patch("week2.app.POLICY_CHUNKS", []),
            patch("week2.app.generate_grounded_text", fail_if_called),
        ):
            result = run_expense_review(self.claim())

        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["citations"], [])
        self.assertIsNone(result["review_summary"])

    def test_api_rejects_an_amount_above_the_precheck_ceiling(self):
        response = self.client.post(
            "/review",
            json={"amount": 2_000_000, "receipt_attached": True, "purpose": "교통비"},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.documents import Document

from shared.live_rag import LiveRagConfigurationError, LiveRagSettings, is_live_mode
from week1.app import create_app as create_week1_app, run_query
from week2.app import ExpenseRequest, run_expense_review
from week3.app import ChangeRequest, run_change_review


class LiveRagSettingsTests(unittest.TestCase):
    def test_fixture_is_the_safe_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_live_mode())

    def test_live_requires_an_openai_key_and_database_url(self):
        with patch.dict(os.environ, {"APP_MODE": "live"}, clear=True):
            with self.assertRaises(LiveRagConfigurationError):
                LiveRagSettings.from_environment()

    def test_live_reads_the_explicit_configuration(self):
        with patch.dict(
            os.environ,
            {
                "APP_MODE": "live",
                "OPENAI_API_KEY": "test-key",
                "DATABASE_URL": "postgresql+psycopg://user:password@localhost:5432/db",
                "RAG_RETRIEVAL_K": "3",
                "RAG_MIN_RELEVANCE": "0.7",
            },
            clear=True,
        ):
            settings = LiveRagSettings.from_environment()

        self.assertEqual(settings.retrieval_k, 3)
        self.assertEqual(settings.min_relevance, 0.7)
        self.assertEqual(settings.embedding_model, "text-embedding-3-small")

    def test_week1_live_path_generates_only_from_retrieved_documents(self):
        evidence = [
            Document(
                page_content="휴가 신청은 최소 3일 전에 한다.",
                metadata={"document_id": "leave-policy", "chunk_id": "leave-policy-01"},
            )
        ]
        with (
            patch.dict(os.environ, {"APP_MODE": "live"}, clear=True),
            patch("week1.app.retrieve_documents", return_value=evidence) as retrieve,
            patch("week1.app.generate_grounded_text", return_value="휴가는 3일 전에 신청하세요.") as generate,
        ):
            result = run_query("휴가 신청은 언제 하나요?")

        retrieve.assert_called_once()
        generate.assert_called_once()
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["answer"], "휴가는 3일 전에 신청하세요.")
        self.assertEqual(result["citations"][0]["document_id"], "leave-policy")

    def test_live_without_retrieved_evidence_ends_safely(self):
        with (
            patch.dict(os.environ, {"APP_MODE": "live"}, clear=True),
            patch("week2.app.retrieve_documents", return_value=[]),
            patch("week3.app.retrieve_documents", return_value=[]),
        ):
            week2 = run_expense_review(
                ExpenseRequest(amount=10000, receipt_attached=True, purpose="고객 미팅")
            )
            week3 = run_change_review(
                ChangeRequest(request="서버 설정 변경을 검토해 주세요", user_role="manager")
            )

        self.assertEqual(week2["status"], "insufficient_evidence")
        self.assertEqual(week3["status"], "insufficient_evidence")

    def test_live_configuration_failure_becomes_a_service_unavailable_response(self):
        with patch.dict(os.environ, {"APP_MODE": "live"}, clear=True):
            response = TestClient(create_week1_app()).post(
                "/query", json={"question": "휴가 신청은 언제 하나요?"}
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "live_rag_unavailable")


if __name__ == "__main__":
    unittest.main()

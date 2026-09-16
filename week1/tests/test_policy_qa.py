import os
import unittest
from dataclasses import replace
from unittest.mock import patch

from fastapi.testclient import TestClient

from week1.app import (
    POLICY_SOURCE_DOCUMENTS,
    create_app,
    create_fixture_services,
    run_policy_query,
    split_policy_documents,
)


class Week1PolicyQaTests(unittest.TestCase):
    def setUp(self):
        self.services = create_fixture_services()
        self.client = TestClient(create_app(self.services))

    def test_supported_question_returns_grounded_answer(self):
        result = run_policy_query("How early should I request vacation?", self.services)

        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["difficulty"], 1)
        self.assertEqual(result["mode"], "fixture")
        self.assertIn("three business days", result["answer"])
        self.assertEqual(result["citations"][0]["document_id"], "hr-leave-policy")
        self.assertEqual(result["steps"], ["retrieve", "answer", "grounding_guard"])

    def test_policy_sources_are_split_with_recursive_character_splitter(self):
        chunks = split_policy_documents(POLICY_SOURCE_DOCUMENTS, chunk_size=70)

        self.assertGreater(len(chunks), len(POLICY_SOURCE_DOCUMENTS))
        self.assertTrue(all("chunk_id" in chunk.metadata for chunk in chunks))

    def test_unknown_question_stops_without_hallucinating(self):
        result = run_policy_query("What is the office Wi-Fi password?", self.services)

        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["answer"])
        self.assertEqual(result["citations"], [])

    def test_empty_retriever_output_stops_without_calling_answerer(self):
        class EmptyRetriever:
            def search(self, query, *, k=3, filter=None):
                return []

        def fail_if_called(question, documents):
            self.fail("answerer must not run without evidence")

        services = replace(self.services, retriever=EmptyRetriever(), answer=fail_if_called)
        result = run_policy_query("vacation policy", services)
        self.assertEqual(result["status"], "insufficient_evidence")

    def test_api_rejects_too_short_question(self):
        response = self.client.post("/query", json={"question": "?"})
        self.assertEqual(response.status_code, 422)

    def test_api_exposes_fixture_mode_explicitly(self):
        self.assertEqual(self.client.get("/health").json()["mode"], "fixture")
        response = self.client.post("/query", json={"question": "vacation request notice"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "fixture")

    def test_live_mode_requires_openai_and_database_configuration(self):
        clean_env = {key: value for key, value in os.environ.items() if key not in {
            "OPENAI_API_KEY", "DATABASE_URL", "APP_MODE"
        }}
        with patch.dict(os.environ, clean_env, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                create_app(mode="live")

    def test_unknown_app_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "APP_MODE"):
            create_app(mode="preview")


if __name__ == "__main__":
    unittest.main()

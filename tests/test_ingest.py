import unittest

from shared.ingest import markdown_documents


class MarkdownIngestionTests(unittest.TestCase):
    def test_each_week_has_a_reviewable_markdown_source_and_stable_metadata(self):
        expected_documents = {
            "week1": {"leave-policy", "leave-handover-checklist"},
            "week2": {"expense-policy", "expense-evidence-guide"},
            "week3": {"security-policy", "change-request-template"},
        }
        for week, expected_ids in expected_documents.items():
            documents = markdown_documents(week)
            self.assertTrue(documents)
            self.assertTrue(expected_ids.issubset({doc.metadata["document_id"] for doc in documents}))
            self.assertTrue(documents[0].metadata["chunk_id"])
            self.assertTrue(documents[0].metadata["source"].endswith(".md"))
            self.assertEqual(documents[0].metadata["week"], week)


if __name__ == "__main__":
    unittest.main()

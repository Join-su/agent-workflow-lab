import unittest

from langchain_core.documents import Document

from lab_core import PGVectorRetriever


class LiveRetrievalContractTests(unittest.TestCase):
    def test_low_relevance_documents_are_removed(self):
        relevant = Document(
            page_content="vacation notice",
            metadata={"document_id": "hr", "chunk_id": "hr-1"},
        )
        unrelated = Document(
            page_content="office wifi",
            metadata={"document_id": "it", "chunk_id": "it-1"},
        )

        class Store:
            def similarity_search_with_relevance_scores(self, query, *, k, filter):
                self.call = (query, k, filter)
                return [(relevant, 0.81), (unrelated, 0.12)]

        store = Store()
        retriever = PGVectorRetriever(store, min_relevance_score=0.35)

        self.assertEqual(
            retriever.search("vacation", k=2, filter={"category": "hr"}),
            [relevant],
        )
        self.assertEqual(store.call, ("vacation", 2, {"category": "hr"}))


if __name__ == "__main__":
    unittest.main()

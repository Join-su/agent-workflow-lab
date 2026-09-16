import unittest

from fastapi.testclient import TestClient

from labs.week1_policy_qa import create_app


class Week1PolicyQaTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())

    def test_supported_question_uses_retriever_and_answer_agent(self):
        response = self.client.post(
            "/query", json={"question": "휴가 신청은 며칠 전에 해야 하나요?"}
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "answered")
        self.assertEqual(body["difficulty"], 1)
        self.assertEqual(body["agents_run"], ["retriever", "answer"])
        self.assertEqual(body["citations"][0]["document_id"], "leave-policy")


if __name__ == "__main__":
    unittest.main()

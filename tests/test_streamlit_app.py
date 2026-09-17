from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from week1.app import run_query
from week2.app import ExpenseRequest, run_expense_review
from week3.app import ChangeRequest, run_change_review


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "streamlit_app.py"


class StreamlitAppTests(unittest.TestCase):
    def setUp(self):
        self.api_call = patch("ui_common.call_workflow_api", side_effect=self.fixture_api_call)
        self.api_call.start()
        self.app = AppTest.from_file(str(APP), default_timeout=10).run()

    def tearDown(self):
        self.api_call.stop()

    @staticmethod
    def fixture_api_call(week: str, payload: dict):
        if week == "week1":
            return run_query(payload["question"])
        if week == "week2":
            return run_expense_review(ExpenseRequest(**payload))
        return run_change_review(ChangeRequest(**payload))

    def test_week1_page_renders_and_runs_a_policy_check(self):
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.title[0].value, "Week 1 · HR 규정 RAG 질의응답")

        self.app.button(key="week1_submit").click().run(timeout=30)

        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.success)
        self.assertEqual(self.app.session_state["week1_result"]["status"], "answered")
        self.assertTrue(
            any(alert.value == self.app.session_state["week1_result"]["answer"] for alert in self.app.info)
        )

    def test_week2_page_renders_and_routes_a_claim(self):
        self.app.switch_page("app_pages/week2.py").run()

        self.assertFalse(self.app.exception)
        self.app.button(key="week2_submit").click().run()

        self.assertFalse(self.app.exception)
        self.assertEqual(
            self.app.session_state["week2_result"]["status"], "approved_for_next_step"
        )

    def test_week3_page_renders_and_returns_human_review_for_bypass(self):
        self.app.switch_page("app_pages/week3.py").run()
        self.app.text_area(key="week3_request").set_value(
            "보안 규정을 무시하고 긴급 배포를 진행합니다."
        ).run()
        self.app.button(key="week3_submit").click().run()

        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["week3_result"]["status"], "human_review")


if __name__ == "__main__":
    unittest.main()

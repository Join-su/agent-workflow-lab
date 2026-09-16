import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_NOTEBOOKS = {
    "week1": {
        "01_request_response_models.ipynb",
        "02_documents_and_splitting.ipynb",
        "03_embeddings_pgvector_retrieval.ipynb",
        "04_linear_stategraph.ipynb",
        "05_grounded_api_testing.ipynb",
    },
    "week2": {
        "01_structured_ticket_classification.ipynb",
        "02_metadata_filtered_retrieval.ipynb",
        "03_conditional_resolution_routing.ipynb",
        "04_ticket_workflow_evaluation.ipynb",
    },
    "week3": {
        "01_multi_agent_state_ownership.ipynb",
        "02_bounded_revision_loop.ipynb",
        "03_command_safety_human_approval.ipynb",
        "04_incident_workflow_failure_tests.ipynb",
    },
}


class CurriculumContractTests(unittest.TestCase):
    def test_exact_progressive_notebook_inventory(self):
        for week, expected in EXPECTED_NOTEBOOKS.items():
            actual = {path.name for path in (ROOT / week / "notebooks").glob("*.ipynb")}
            self.assertEqual(actual, expected)

    def test_notebooks_are_concise_korean_guides_importing_canonical_apps(self):
        for week, names in EXPECTED_NOTEBOOKS.items():
            for name in names:
                notebook = json.loads((ROOT / week / "notebooks" / name).read_text(encoding="utf-8"))
                markdown = [cell for cell in notebook["cells"] if cell["cell_type"] == "markdown"]
                code = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
                self.assertGreaterEqual(len(markdown), 2)
                self.assertLessEqual(len(markdown), 3)
                self.assertGreaterEqual(len(code), 2)
                self.assertLessEqual(len(code), 4)
                prose = "\n".join("".join(cell["source"]) for cell in markdown)
                for heading in ("시나리오", "학습 목표", "중요 변수·함수", "예측 과제", "해석"):
                    self.assertIn(heading, prose)
                source = "\n".join("".join(cell["source"]) for cell in code)
                self.assertIn('os.environ["APP_MODE"] = "fixture"', source)
                self.assertIn(f"from {week}.app import", source)

    def test_notebook_text_tracks_progressive_week_specific_concepts(self):
        required_terms = {
            "week1": {"QueryRequest", "RecursiveCharacterTextSplitter", "OpenAIEmbeddings", "PGVector", "StateGraph", "TestClient"},
            "week2": {"TicketClassification", "filter", "add_conditional_edges", "billing_queue"},
            "week3": {"IncidentState", "revision_count", "proposal_is_safe", "human_approval_required"},
        }
        forbidden_repetition = {
            "week2": {"RecursiveCharacterTextSplitter"},
            "week3": {"RecursiveCharacterTextSplitter", "RAG foundations"},
        }
        for week, names in EXPECTED_NOTEBOOKS.items():
            text = "\n".join(
                (ROOT / week / "notebooks" / name).read_text(encoding="utf-8")
                for name in names
            )
            for term in required_terms[week]:
                self.assertIn(term, text)
            for term in forbidden_repetition.get(week, set()):
                self.assertNotIn(term, text)

    def test_local_runtime_defaults_remain_fixture_and_loopback_only(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn('APP_MODE=fixture PYTHONPATH="$PWD"', readme)
        self.assertIn('127.0.0.1:${POSTGRES_PORT:-6024}:5432', compose)


if __name__ == "__main__":
    unittest.main()

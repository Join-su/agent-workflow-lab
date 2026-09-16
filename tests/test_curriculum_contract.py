import ast
import io
import json
import tokenize
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

REQUIRED_CODE_TERMS = {
    "week1/notebooks/01_request_response_models.ipynb": {"class PracticeQuery", "class PracticeResponse", "BaseModel", "Field(", "ValidationError"},
    "week1/notebooks/02_documents_and_splitting.ipynb": {"Document(", "RecursiveCharacterTextSplitter", ".split_documents("},
    "week1/notebooks/03_embeddings_pgvector_retrieval.ipynb": {"class MiniEmbedding", "cosine_similarity", "relevance_threshold"},
    "week1/notebooks/04_linear_stategraph.ipynb": {"class PracticeState", "StateGraph(", ".add_node(", ".add_edge(", ".compile(", ".invoke("},
    "week1/notebooks/05_grounded_api_testing.ipynb": {"FastAPI(", "TestClient(", "evidence_gate", "insufficient_evidence"},
    "week2/notebooks/01_structured_ticket_classification.ipynb": {"class TicketClassification", "Literal[", "model_validate("},
    "week2/notebooks/02_metadata_filtered_retrieval.ipynb": {"Document(", "metadata_filter", "category"},
    "week2/notebooks/03_conditional_resolution_routing.ipynb": {"StateGraph(", ".add_conditional_edges(", "choose_route", ".invoke("},
    "week2/notebooks/04_ticket_workflow_evaluation.ipynb": {"classify_ticket", "retrieve_playbook", "evidence_gate", "evaluation_cases"},
    "week3/notebooks/01_multi_agent_state_ownership.ipynb": {"class IncidentState", "OWNERSHIP", "triage_node", "investigator_node", "commander_node"},
    "week3/notebooks/02_bounded_revision_loop.ipynb": {"StateGraph(", "revision_count", "max_revisions", ".add_conditional_edges(", "fail_closed"},
    "week3/notebooks/03_command_safety_human_approval.ipynb": {"class CommandProposal", "proposal_is_safe", "approval_packet", "executed_commands"},
    "week3/notebooks/04_incident_workflow_failure_tests.ipynb": {"failure_cases", "practice_validate_severity", "blocked_manual_review", "executed_commands", "assert"},
}

FORBIDDEN_CODE_TERMS = {
    "from week1.app",
    "from week2.app",
    "from week3.app",
    "import week1.app",
    "import week2.app",
    "import week3.app",
    "run_policy_query",
    "run_ticket_workflow",
    "run_incident_response",
    "create_fixture_services",
    "create_app",
    "build_workflow",
}


class CurriculumContractTests(unittest.TestCase):
    def load_notebook(self, relative_path: str) -> dict:
        return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))

    def notebook_parts(self, relative_path: str) -> tuple[str, str, list[dict], list[dict]]:
        notebook = self.load_notebook(relative_path)
        markdown = [cell for cell in notebook["cells"] if cell["cell_type"] == "markdown"]
        code = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        prose = "\n".join("".join(cell["source"]) for cell in markdown)
        source = "\n".join("".join(cell["source"]) for cell in code)
        return prose, source, markdown, code

    def execute_notebook_code(self, relative_path: str) -> dict:
        namespace: dict = {}
        notebook = self.load_notebook(relative_path)
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                exec(compile("".join(cell["source"]), f"{relative_path}:{cell['id']}", "exec"), namespace)
        return namespace

    def test_exact_progressive_notebook_inventory(self):
        for week, expected in EXPECTED_NOTEBOOKS.items():
            actual = {path.name for path in (ROOT / week / "notebooks").glob("*.ipynb")}
            self.assertEqual(actual, expected)

    def test_notebooks_build_independent_primitives_without_canonical_app_imports(self):
        all_comments: list[str] = []
        for relative_path, required_terms in REQUIRED_CODE_TERMS.items():
            with self.subTest(notebook=relative_path):
                prose, source, markdown, code = self.notebook_parts(relative_path)
                self.assertGreaterEqual(len(markdown), 3)
                self.assertGreaterEqual(len(code), 3)
                for heading in ("시나리오", "학습 목표", "직접 조립", "중간 결과", "실제 app 연결", "실패 경계"):
                    self.assertIn(heading, prose)
                self.assertIn("다음 Notebook 연결", prose)
                for forbidden in FORBIDDEN_CODE_TERMS:
                    self.assertNotIn(forbidden, source)
                for required in required_terms:
                    self.assertIn(required, source)

                for cell in code:
                    cell_source = "".join(cell["source"])
                    comments = [
                        token.string
                        for token in tokenize.generate_tokens(io.StringIO(cell_source).readline)
                        if token.type == tokenize.COMMENT
                    ]
                    self.assertGreaterEqual(len(comments), 2, (relative_path, cell["id"], comments))
                    self.assertNotIn("핵심 객체·함수의 입력이 어떤 state 또는 output으로 바뀌는지 확인합니다.", cell_source)
                    all_comments.extend(comments)

                    source_lines = cell_source.splitlines()
                    tree = ast.parse(cell_source)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                            preceding = source_lines[max(0, node.lineno - 3):node.lineno - 1]
                            self.assertTrue(
                                any(line.lstrip().startswith("#") for line in preceding),
                                (relative_path, cell["id"], node.name),
                            )

        self.assertGreaterEqual(len(set(all_comments)), int(len(all_comments) * 0.7))

    def test_notebook_code_uses_small_local_fixtures_and_assertions(self):
        for relative_path in REQUIRED_CODE_TERMS:
            with self.subTest(notebook=relative_path):
                _, source, _, _ = self.notebook_parts(relative_path)
                self.assertIn("assert ", source)
                self.assertTrue(any(marker in source for marker in ("practice_", "mini_", "sample_", "evaluation_cases", "failure_cases")))

    def test_langgraph_is_reused_for_distinct_week_specific_patterns(self):
        week1 = self.notebook_parts("week1/notebooks/04_linear_stategraph.ipynb")[1]
        week2 = self.notebook_parts("week2/notebooks/03_conditional_resolution_routing.ipynb")[1]
        week3 = self.notebook_parts("week3/notebooks/02_bounded_revision_loop.ipynb")[1]

        self.assertIn(".add_edge(", week1)
        self.assertNotIn(".add_conditional_edges(", week1)
        self.assertIn(".add_conditional_edges(", week2)
        self.assertIn("choose_route", week2)
        self.assertIn(".add_conditional_edges(", week3)
        self.assertIn("revision_count", week3)
        self.assertIn("max_revisions", week3)

    def test_notebook_imports_and_calls_are_ast_checked(self):
        forbidden_modules = {"week1.app", "week2.app", "week3.app"}
        forbidden_calls = {
            "run_policy_query", "run_ticket_workflow", "run_incident_response",
            "create_fixture_services", "create_app", "build_workflow",
        }
        for relative_path in REQUIRED_CODE_TERMS:
            notebook = self.load_notebook(relative_path)
            for cell in notebook["cells"]:
                if cell["cell_type"] != "code":
                    continue
                tree = ast.parse("".join(cell["source"]))
                imports = {
                    alias.name
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Import)
                    for alias in node.names
                }
                imports.update(
                    node.module or ""
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom)
                )
                imports.update(
                    f"{node.module}.{alias.name}" if node.module else alias.name
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom)
                    for alias in node.names
                )
                calls = {
                    node.func.id
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                }
                calls.update(
                    node.func.attr
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                )
                self.assertTrue(imports.isdisjoint(forbidden_modules), (relative_path, imports))
                self.assertTrue(calls.isdisjoint(forbidden_calls), (relative_path, calls))

    def test_week3_notebook_guards_reject_shell_control_and_expansion(self):
        safety = self.execute_notebook_code("week3/notebooks/03_command_safety_human_approval.ipynb")
        failure = self.execute_notebook_code("week3/notebooks/04_incident_workflow_failure_tests.ipynb")
        unsafe_commands = [
            "kubectl get pods\nkubectl delete namespace production",
            "kubectl get pods > /tmp/leak",
            "kubectl get pods & kubectl delete pod checkout",
            "kubectl get $SECRET",
            "kubectl get pods `whoami`",
            "kubectl get pods \\ --namespace production",
        ]
        for command in unsafe_commands:
            with self.subTest(command=command):
                proposal = safety["CommandProposal"](command=command, purpose="unsafe", dry_run=True)
                self.assertFalse(safety["proposal_is_safe"](proposal))
                result = failure["practice_incident_guard"]([command], revision_count=1, max_revisions=1)
                self.assertEqual(result["status"], "blocked_manual_review")
                self.assertEqual(result["approval_packet"]["proposed_commands"], [])
                self.assertEqual(result["executed_commands"], [])

        mixed_proposals = [
            safety["CommandProposal"](command="kubectl get pods -n shop", purpose="safe", dry_run=True),
            safety["CommandProposal"](command="kubectl delete namespace production", purpose="unsafe", dry_run=True),
        ]
        mixed_packet = safety["build_approval_packet"](mixed_proposals)
        self.assertEqual(mixed_packet["status"], "blocked_manual_review")
        self.assertEqual(mixed_packet["approval_packet"]["proposed_commands"], [])
        self.assertEqual(mixed_packet["executed_commands"], [])

        mixed = failure["practice_incident_guard"](
            ["kubectl get pods -n shop", "kubectl delete namespace production"],
            revision_count=1,
            max_revisions=1,
        )
        self.assertEqual(mixed["status"], "blocked_manual_review")
        self.assertEqual(mixed["approval_packet"]["proposed_commands"], [])
        self.assertEqual(mixed["executed_commands"], [])

        self.assertEqual(failure["practice_validate_severity"]("SEV1"), "SEV1")
        with self.assertRaises(ValueError):
            failure["practice_validate_severity"]("SEV0")

    def test_week2_fallback_and_week3_severity_semantics_match_apps(self):
        ticket = self.execute_notebook_code("week2/notebooks/04_ticket_workflow_evaluation.ipynb")
        fallback = ticket["practice_ticket_pipeline"]("Pricing question")
        self.assertEqual(fallback["category"], "other")
        self.assertEqual(fallback["route"], "general_queue")
        self.assertEqual(fallback["status"], "needs_more_information")

        safety = self.execute_notebook_code("week3/notebooks/03_command_safety_human_approval.ipynb")
        failure = self.execute_notebook_code("week3/notebooks/04_incident_workflow_failure_tests.ipynb")
        observe_proposal = safety["CommandProposal"](
            command="observe checkout error-rate dashboard",
            purpose="SEV3 관찰 계획",
            dry_run=True,
        )
        self.assertTrue(safety["proposal_is_safe"](observe_proposal))
        sev3_packet = safety["build_approval_packet"]([observe_proposal], severity="SEV3")
        self.assertEqual(sev3_packet["status"], "plan_ready")
        self.assertEqual(
            [item["command"] for item in sev3_packet["observation_plan"]["proposed_commands"]],
            [observe_proposal.command],
        )
        self.assertIsNone(sev3_packet["approval_packet"])
        self.assertEqual(sev3_packet["executed_commands"], [])

        sev2_packet = safety["build_approval_packet"]([observe_proposal], severity="SEV2")
        self.assertEqual(sev2_packet["status"], "human_approval_required")
        self.assertIsNone(sev2_packet["observation_plan"])
        self.assertEqual(len(sev2_packet["approval_packet"]["proposed_commands"]), 1)

        sev3_guard = failure["practice_incident_guard"](
            [observe_proposal.command], revision_count=0, max_revisions=1, severity="SEV3"
        )
        self.assertEqual(sev3_guard["status"], "plan_ready")
        self.assertEqual(sev3_guard["observation_plan"]["proposed_commands"], [observe_proposal.command])
        self.assertIsNone(sev3_guard["approval_packet"])
        self.assertEqual(sev3_guard["executed_commands"], [])

    def test_local_runtime_defaults_remain_fixture_and_loopback_only(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn('APP_MODE=fixture PYTHONPATH="$PWD"', readme)
        self.assertIn('127.0.0.1:${POSTGRES_PORT:-6024}:5432', compose)


if __name__ == "__main__":
    unittest.main()

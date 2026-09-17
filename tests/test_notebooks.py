import json
from pathlib import Path
import unittest


class NotebookPythonSyntaxTests(unittest.TestCase):
    def test_notebook_code_uses_python_boolean_literals(self):
        offenders = []
        for notebook in Path(".").glob("week*/notebooks/*.ipynb"):
            payload = json.loads(notebook.read_text(encoding="utf-8"))
            source = "\n".join(
                "".join(cell.get("source", []))
                for cell in payload["cells"]
                if cell.get("cell_type") == "code"
            )
            if '"receipt_attached": false' in source or '"receipt_attached": true' in source:
                offenders.append(str(notebook))

        self.assertEqual(offenders, [])

    def test_langchain_rag_notebooks_invoke_their_imported_chain(self):
        for week in ("week2", "week3"):
            notebook = Path(week) / "notebooks/02_langchain_rag.ipynb"
            payload = json.loads(notebook.read_text(encoding="utf-8"))
            source = "\n".join(
                "".join(cell.get("source", []))
                for cell in payload["cells"]
                if cell.get("cell_type") == "code"
            )

            self.assertIn("policy_retrieval_chain.invoke", source)
            self.assertNotIn("\nretrieval_chain.invoke", source)

    def test_notebooks_are_concise_scenario_guides(self):
        for notebook in Path(".").glob("week*/notebooks/*.ipynb"):
            payload = json.loads(notebook.read_text(encoding="utf-8"))
            markdown = ["".join(cell.get("source", [])) for cell in payload["cells"] if cell.get("cell_type") == "markdown"]
            code = ["".join(cell.get("source", [])) for cell in payload["cells"] if cell.get("cell_type") == "code"]
            joined_markdown = "\n".join(markdown)

            self.assertGreaterEqual(len(markdown), 2, notebook)
            self.assertGreaterEqual(len(code), 2, notebook)
            self.assertIn("시나리오", joined_markdown, notebook)
            self.assertIn("전체 코드 연결", joined_markdown, notebook)
            self.assertTrue(all("#" in cell for cell in code), notebook)

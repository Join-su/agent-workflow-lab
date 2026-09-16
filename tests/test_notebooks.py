import json
from pathlib import Path
import unittest


class NotebookPythonSyntaxTests(unittest.TestCase):
    def test_notebook_code_uses_python_boolean_literals(self):
        offenders = []
        for notebook in Path(".").glob("week*/notebooks/*.ipynb"):
            payload = json.loads(notebook.read_text())
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
            payload = json.loads(notebook.read_text())
            source = "\n".join(
                "".join(cell.get("source", []))
                for cell in payload["cells"]
                if cell.get("cell_type") == "code"
            )

            self.assertIn("policy_retrieval_chain.invoke", source)
            self.assertNotIn("\nretrieval_chain.invoke", source)

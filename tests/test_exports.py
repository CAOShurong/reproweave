from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common import full_ratings, make_workspace

from reproweave.exports import assessment_markdown, matrix_csv, plan_markdown


class ExportTests(unittest.TestCase):
    def test_csv_header(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            self.assertTrue(matrix_csv(workspace).startswith("paper_id,title,year,method"))

    def test_csv_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            self.assertIn("paper-one,Paper One,2025", matrix_csv(workspace))

    def test_plan_heading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            self.assertIn("# Replication plan: Test review", plan_markdown(workspace))

    def test_plan_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add("task", {"id": "one", "title": "Do one", "estimate_hours": 2})
            self.assertIn("### Do one", plan_markdown(workspace))

    def test_card_boundary(self) -> None:
        card = assessment_markdown(
            {"ratings": full_ratings()},
            {"title": "Paper"},
        )
        self.assertIn("not scientific quality", card)


if __name__ == "__main__":
    unittest.main()

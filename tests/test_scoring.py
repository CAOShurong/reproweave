from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common import full_ratings, make_workspace

from reproweave.scoring import assess_workspace, evidence_matrix, score_assessment


class ScoringTests(unittest.TestCase):
    def test_all_yes_is_100(self) -> None:
        result = score_assessment({"id": "a", "paper_id": "p", "ratings": full_ratings()})
        self.assertEqual(result["score"], 100.0)

    def test_all_no_is_zero(self) -> None:
        result = score_assessment({"id": "a", "paper_id": "p", "ratings": full_ratings("no")})
        self.assertEqual(result["score"], 0.0)

    def test_partial_is_50(self) -> None:
        result = score_assessment({"id": "a", "paper_id": "p", "ratings": full_ratings("partial")})
        self.assertEqual(result["score"], 50.0)

    def test_na_excluded(self) -> None:
        ratings = full_ratings()
        ratings["compute"] = {"rating": "na", "evidence": "Not applicable."}
        result = score_assessment({"id": "a", "paper_id": "p", "ratings": ratings})
        self.assertEqual(result["score"], 100.0)

    def test_missing_dimensions_lower_coverage(self) -> None:
        result = score_assessment(
            {
                "id": "a",
                "paper_id": "p",
                "ratings": {"code": {"rating": "yes", "evidence": "Repository."}},
            }
        )
        self.assertEqual(result["rubric_coverage"], 12.5)

    def test_workspace_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add(
                "assessment",
                {"id": "assessment-one", "paper_id": "paper-one", "ratings": full_ratings()},
            )
            result = assess_workspace(workspace)
            self.assertEqual(result["summary"]["mean_score"], 100.0)

    def test_unassessed_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            result = assess_workspace(workspace)
            self.assertEqual(result["summary"]["unassessed_paper_ids"], ["paper-one"])

    def test_matrix_marks_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            row = evidence_matrix(workspace)["rows"][0]
            self.assertEqual(row["method"], "missing")


if __name__ == "__main__":
    unittest.main()

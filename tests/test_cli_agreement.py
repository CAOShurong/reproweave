from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from common import full_ratings, make_workspace

from reproweave.assessments import assessment_digest
from reproweave.cli import _parser, run


class AgreementCliTests(unittest.TestCase):
    def test_conflict_is_reported_and_returns_distinct_nonzero_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            for assessment_id, rating in (("review-one", "yes"), ("review-two", "no")):
                workspace.add(
                    "assessment",
                    {
                        "id": assessment_id,
                        "paper_id": "paper-one",
                        "ratings": full_ratings(rating),
                    },
                )
            output = io.StringIO()
            args = _parser().parse_args(["agreement", "--workspace", str(workspace.root)])
            with contextlib.redirect_stdout(output):
                code = run(args)
            result = json.loads(output.getvalue())
            self.assertEqual(code, 4)
            self.assertEqual(result["papers"][0]["status"], "conflict")
            self.assertIsNone(result["papers"][0]["selected_assessment_id"])

    def test_consensus_returns_success_and_selected_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            for assessment_id, rating in (("review-one", "yes"), ("review-two", "no")):
                workspace.add(
                    "assessment",
                    {
                        "id": assessment_id,
                        "paper_id": "paper-one",
                        "ratings": full_ratings(rating),
                    },
                )
            workspace.add(
                "assessment",
                {
                    "id": "consensus-one",
                    "paper_id": "paper-one",
                    "kind": "consensus",
                    "source_assessment_ids": ["review-one", "review-two"],
                    "source_assessment_hashes": {
                        source_id: assessment_digest(workspace.get("assessment", source_id))
                        for source_id in ("review-one", "review-two")
                    },
                    "ratings": full_ratings("partial"),
                },
            )
            output = io.StringIO()
            args = _parser().parse_args(["agreement", "--workspace", str(workspace.root)])
            with contextlib.redirect_stdout(output):
                code = run(args)
            result = json.loads(output.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(result["papers"][0]["selected_assessment_id"], "consensus-one")


if __name__ == "__main__":
    unittest.main()

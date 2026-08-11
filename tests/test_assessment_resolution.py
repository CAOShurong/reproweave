from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common import full_ratings, make_workspace

from reproweave.assessments import (
    assessment_digest,
    build_assessment_resolution,
    resolved_assessment_index,
)
from reproweave.errors import ValidationError
from reproweave.scoring import assess_workspace, evidence_matrix


def _assessment(
    assessment_id: str,
    rating: str,
    *,
    kind: str = "individual",
    sources: list[str] | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "id": assessment_id,
        "paper_id": "paper-one",
        "kind": kind,
        "reviewer": assessment_id,
        "ratings": full_ratings(rating),
    }
    if sources is not None:
        value["source_assessment_ids"] = sources
    return value


def _consensus(
    workspace,
    assessment_id: str,
    rating: str,
    sources: list[str],
) -> dict[str, object]:
    value = _assessment(assessment_id, rating, kind="consensus", sources=sources)
    hashes = {}
    for source_id in sources:
        try:
            hashes[source_id] = assessment_digest(workspace.get("assessment", source_id))
        except (FileNotFoundError, ValidationError):
            hashes[source_id] = "sha256:" + "0" * 64
    value["source_assessment_hashes"] = hashes
    return value


class AssessmentResolutionTests(unittest.TestCase):
    def test_single_legacy_assessment_is_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add(
                "assessment",
                {"id": "legacy", "paper_id": "paper-one", "ratings": full_ratings()},
            )
            result = build_assessment_resolution(workspace)
            self.assertEqual(result["papers"][0]["status"], "resolved")
            self.assertEqual(result["papers"][0]["selected_assessment_id"], "legacy")

    def test_conflicting_individual_reviews_are_not_silently_aggregated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add("assessment", _assessment("review-one", "yes"))
            workspace.add("assessment", _assessment("review-two", "no"))
            result = build_assessment_resolution(workspace)
            row = result["papers"][0]
            self.assertEqual(row["status"], "conflict")
            self.assertEqual(set(row["conflicting_dimensions"]), set(full_ratings()))
            self.assertIsNone(row["selected_assessment_id"])
            with self.assertRaisesRegex(ValidationError, "consensus"):
                resolved_assessment_index(workspace)
            with self.assertRaises(ValidationError):
                assess_workspace(workspace)
            with self.assertRaises(ValidationError):
                evidence_matrix(workspace)

    def test_matching_individual_reviews_still_require_explicit_consensus(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add("assessment", _assessment("review-one", "yes"))
            workspace.add("assessment", _assessment("review-two", "yes"))
            result = build_assessment_resolution(workspace)
            row = result["papers"][0]
            self.assertEqual(row["status"], "conflict")
            self.assertEqual(row["conflicting_dimensions"], [])
            self.assertIsNone(row["selected_assessment_id"])

    def test_explicit_consensus_resolves_conflict_without_removing_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add("assessment", _assessment("review-one", "yes"))
            workspace.add("assessment", _assessment("review-two", "no"))
            workspace.add(
                "assessment",
                _consensus(
                    workspace,
                    "consensus-one",
                    "partial",
                    ["review-one", "review-two"],
                ),
            )
            result = build_assessment_resolution(workspace)
            row = result["papers"][0]
            self.assertEqual(row["status"], "resolved")
            self.assertEqual(row["selected_assessment_id"], "consensus-one")
            self.assertEqual(row["individual_assessment_ids"], ["review-one", "review-two"])
            self.assertEqual(assess_workspace(workspace)["summary"]["mean_score"], 50.0)
            self.assertEqual(evidence_matrix(workspace)["rows"][0]["method"], "partial")

    def test_consensus_sources_must_exist_and_match_the_paper(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add("assessment", _assessment("review-one", "yes"))
            workspace.add(
                "assessment",
                _consensus(
                    workspace,
                    "consensus-one",
                    "yes",
                    ["review-one", "missing-review"],
                ),
            )
            result = build_assessment_resolution(workspace)
            self.assertEqual(result["papers"][0]["status"], "invalid")
            self.assertIn(
                "assessment.consensus_source_missing",
                {item["code"] for item in result["issues"]},
            )

    def test_consensus_must_cover_every_individual_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            for reviewer in ("review-one", "review-two", "review-three"):
                workspace.add("assessment", _assessment(reviewer, "yes"))
            workspace.add(
                "assessment",
                _consensus(
                    workspace,
                    "consensus-one",
                    "yes",
                    ["review-one", "review-two"],
                ),
            )
            result = build_assessment_resolution(workspace)
            self.assertEqual(result["papers"][0]["status"], "invalid")
            self.assertIn(
                "assessment.consensus_incomplete",
                {item["code"] for item in result["issues"]},
            )

    def test_consensus_cannot_use_cross_paper_or_consensus_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add(
                "paper",
                {
                    "id": "paper-two",
                    "title": "Paper Two",
                    "authors": ["B. Author"],
                    "year": 2025,
                },
            )
            workspace.add("assessment", _assessment("review-one", "yes"))
            cross_paper = _assessment("review-two", "yes")
            cross_paper["paper_id"] = "paper-two"
            workspace.add("assessment", cross_paper)
            other_consensus = _consensus(
                workspace,
                "consensus-two",
                "yes",
                ["review-one", "review-two"],
            )
            other_consensus["paper_id"] = "paper-two"
            workspace.add("assessment", other_consensus)
            workspace.add(
                "assessment",
                _consensus(
                    workspace,
                    "consensus-one",
                    "yes",
                    ["review-one", "review-two", "consensus-two"],
                ),
            )
            result = build_assessment_resolution(workspace)
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("assessment.consensus_source_not_individual", codes)
            self.assertIn("assessment.consensus_source_paper_mismatch", codes)

    def test_only_one_consensus_is_allowed_per_paper(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add("assessment", _assessment("review-one", "yes"))
            workspace.add("assessment", _assessment("review-two", "no"))
            for consensus_id in ("consensus-one", "consensus-two"):
                workspace.add(
                    "assessment",
                    _consensus(
                        workspace,
                        consensus_id,
                        "partial",
                        ["review-one", "review-two"],
                    ),
                )
            result = build_assessment_resolution(workspace)
            self.assertEqual(result["papers"][0]["status"], "invalid")
            self.assertIn(
                "assessment.consensus_multiple",
                {item["code"] for item in result["issues"]},
            )

    def test_changed_source_requires_a_new_consensus(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add("assessment", _assessment("review-one", "yes"))
            workspace.add("assessment", _assessment("review-two", "no"))
            workspace.add(
                "assessment",
                _consensus(
                    workspace,
                    "consensus-one",
                    "partial",
                    ["review-one", "review-two"],
                ),
            )
            changed = workspace.get("assessment", "review-one")
            changed["ratings"]["method"]["evidence"] = "Changed after consensus."
            workspace.add("assessment", changed, replace=True)
            result = build_assessment_resolution(workspace)
            self.assertEqual(result["papers"][0]["status"], "invalid")
            self.assertIn(
                "assessment.consensus_source_changed",
                {item["code"] for item in result["issues"]},
            )
            with self.assertRaises(ValidationError):
                assess_workspace(workspace)


if __name__ == "__main__":
    unittest.main()

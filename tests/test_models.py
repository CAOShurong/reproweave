from __future__ import annotations

import math
import unittest

from common import full_ratings

from reproweave.errors import ValidationError
from reproweave.models import validate


class ModelTests(unittest.TestCase):
    def test_valid_paper(self) -> None:
        item = {"id": "p", "title": "T", "authors": ["A"], "year": 2020}
        self.assertIs(validate("paper", item), item)

    def test_paper_requires_authors(self) -> None:
        with self.assertRaises(ValidationError):
            validate("paper", {"id": "p", "title": "T", "authors": [], "year": 2020})

    def test_paper_year_range(self) -> None:
        with self.assertRaises(ValidationError):
            validate("paper", {"id": "p", "title": "T", "authors": ["A"], "year": 20})

    def test_claim_type(self) -> None:
        with self.assertRaises(ValidationError):
            validate(
                "claim",
                {
                    "id": "c",
                    "paper_id": "p",
                    "statement": "S",
                    "evidence_locator": "p. 1",
                    "type": "marketing",
                },
            )

    def test_resource_kind(self) -> None:
        with self.assertRaises(ValidationError):
            validate("resource", {"id": "r", "name": "R", "kind": "secret"})

    def test_assessment_valid(self) -> None:
        item = {"id": "a", "paper_id": "p", "ratings": full_ratings()}
        self.assertIs(validate("assessment", item), item)

    def test_assessment_rejects_unknown_dimension(self) -> None:
        with self.assertRaises(ValidationError):
            validate(
                "assessment",
                {
                    "id": "a",
                    "paper_id": "p",
                    "ratings": {"magic": {"rating": "yes", "evidence": "x"}},
                },
            )

    def test_assessment_requires_evidence(self) -> None:
        with self.assertRaises(ValidationError):
            validate(
                "assessment",
                {"id": "a", "paper_id": "p", "ratings": {"code": {"rating": "yes"}}},
            )

    def test_consensus_assessment_requires_two_unique_sources(self) -> None:
        for sources in (None, [], ["review-one"], ["review-one", "review-one"]):
            item = {
                "id": "consensus-one",
                "paper_id": "p",
                "kind": "consensus",
                "ratings": full_ratings(),
            }
            if sources is not None:
                item["source_assessment_ids"] = sources
            with self.subTest(sources=sources), self.assertRaises(ValidationError):
                validate("assessment", item)

    def test_individual_assessment_rejects_consensus_sources(self) -> None:
        for sources in ([], ["review-two", "review-three"]):
            with self.subTest(sources=sources), self.assertRaises(ValidationError):
                validate(
                    "assessment",
                    {
                        "id": "review-one",
                        "paper_id": "p",
                        "kind": "individual",
                        "source_assessment_ids": sources,
                        "ratings": full_ratings(),
                    },
                )

    def test_assessment_rejects_unknown_kind(self) -> None:
        with self.assertRaises(ValidationError):
            validate(
                "assessment",
                {"id": "a", "paper_id": "p", "kind": "majority", "ratings": full_ratings()},
            )

    def test_task_rejects_negative_estimate(self) -> None:
        with self.assertRaises(ValidationError):
            validate("task", {"id": "t", "title": "T", "estimate_hours": -1})

    def test_task_rejects_boolean_and_non_finite_estimates(self) -> None:
        for estimate in (True, False, math.nan, math.inf, -math.inf, 1_000_000_001, 10**400):
            with self.subTest(estimate=estimate), self.assertRaises(ValidationError):
                validate("task", {"id": "t", "title": "T", "estimate_hours": estimate})

    def test_screening_requires_reason(self) -> None:
        with self.assertRaises(ValidationError):
            validate(
                "screening",
                {
                    "id": "s",
                    "paper_id": "p",
                    "state": "included",
                    "reason": "",
                    "recorded_at": "2025-01-01T00:00:00Z",
                },
            )

    def test_unknown_kind(self) -> None:
        with self.assertRaises(ValidationError):
            validate("unknown", {})


if __name__ == "__main__":
    unittest.main()

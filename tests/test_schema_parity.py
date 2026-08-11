from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from common import full_ratings
from jsonschema import Draft202012Validator

from reproweave.errors import ValidationError
from reproweave.models import validate

ROOT = Path(__file__).resolve().parents[1]


def load_schema(name: str) -> dict[str, object]:
    return json.loads((ROOT / "schemas" / f"{name}.schema.json").read_text("utf-8"))


def assessment() -> dict[str, object]:
    return {"id": "review-one", "paper_id": "paper-one", "ratings": full_ratings()}


class SchemaParityTests(unittest.TestCase):
    def assert_both_accept(self, kind: str, value: dict[str, object]) -> None:
        cloned = copy.deepcopy(value)
        self.assertIs(validate(kind, cloned), cloned)
        self.assertEqual(list(Draft202012Validator(load_schema(kind)).iter_errors(value)), [])

    def assert_both_reject(self, kind: str, value: dict[str, object]) -> None:
        with self.assertRaises(ValidationError):
            validate(kind, copy.deepcopy(value))
        self.assertTrue(list(Draft202012Validator(load_schema(kind)).iter_errors(value)))

    def test_assessment_runtime_and_schema_share_field_contract(self) -> None:
        valid_individual = assessment()
        valid_individual.update(
            {
                "kind": "individual",
                "reviewer": "Reviewer",
                "assessed_at": "2026-08-11T00:00:00Z",
                "notes": "Notes",
            }
        )
        valid_consensus = assessment()
        valid_consensus.update(
            {
                "id": "consensus-one",
                "kind": "consensus",
                "source_assessment_ids": ["review-one", "review-two"],
                "source_assessment_hashes": {
                    "review-one": "sha256:" + "0" * 64,
                    "review-two": "sha256:" + "1" * 64,
                },
            }
        )
        for value in (assessment(), valid_individual, valid_consensus):
            with self.subTest(valid=value.get("kind", "legacy")):
                self.assert_both_accept("assessment", value)

        invalid_values = []
        for field, invalid in (
            ("reviewer", " "),
            ("reviewer", []),
            ("assessed_at", " "),
            ("assessed_at", 123),
            ("notes", 123),
            ("kind", []),
            ("source_assessment_ids", None),
        ):
            value = assessment()
            value[field] = invalid
            invalid_values.append(value)
        individual_sources = assessment()
        individual_sources["source_assessment_ids"] = []
        invalid_values.append(individual_sources)
        for sources in (None, [], ["review-one"], ["review-one", "review-one"]):
            value = assessment()
            value.update({"id": "consensus-one", "kind": "consensus"})
            if sources is not None:
                value["source_assessment_ids"] = sources
            invalid_values.append(value)
        invalid_rating = assessment()
        invalid_rating["ratings"]["method"]["rating"] = []
        invalid_values.append(invalid_rating)
        blank_evidence = assessment()
        blank_evidence["ratings"]["method"]["evidence"] = " "
        invalid_values.append(blank_evidence)
        invalid_action = assessment()
        invalid_action["ratings"]["method"]["next_action"] = 123
        invalid_values.append(invalid_action)
        too_long = assessment()
        too_long["id"] = "a" + "1" * 200
        invalid_values.append(too_long)

        for index, value in enumerate(invalid_values):
            with self.subTest(invalid=index):
                self.assert_both_reject("assessment", value)

    def test_task_runtime_and_schema_share_numeric_and_list_contract(self) -> None:
        for value in (
            {"id": "task-one", "title": "Task"},
            {
                "id": "task-one",
                "title": "Task",
                "estimate_hours": 1_000_000_000,
                "depends_on": [],
                "paper_ids": [],
            },
        ):
            self.assert_both_accept("task", value)

        invalid_values = [
            {"id": "task-one", "title": "Task", "estimate_hours": True},
            {"id": "task-one", "title": "Task", "estimate_hours": 1_000_000_001},
            {"id": "task-one", "title": "Task", "depends_on": None},
            {"id": "task-one", "title": "Task", "paper_ids": None},
            {"id": "task-one", "title": "Task", "state": []},
            {"id": "task-one", "title": "Task", "priority": {}},
            {"id": "a" + "1" * 200, "title": "Task"},
        ]
        for index, value in enumerate(invalid_values):
            with self.subTest(invalid=index):
                self.assert_both_reject("task", value)

    def test_optional_string_fields_match_every_published_schema(self) -> None:
        fixtures: dict[str, tuple[dict[str, object], tuple[str, ...]]] = {
            "paper": (
                {"id": "paper-one", "title": "Paper", "authors": ["Author"], "year": 2026},
                ("source_key",),
            ),
            "claim": (
                {
                    "id": "claim-one",
                    "paper_id": "paper-one",
                    "statement": "Claim",
                    "evidence_locator": "Page 1",
                },
                ("notes",),
            ),
            "experiment": (
                {
                    "id": "experiment-one",
                    "paper_id": "paper-one",
                    "name": "Experiment",
                    "protocol_summary": "Protocol",
                },
                ("notes",),
            ),
            "resource": (
                {"id": "resource-one", "name": "Resource", "kind": "code"},
                ("notes",),
            ),
            "assessment": (assessment(), ("notes",)),
            "task": ({"id": "task-one", "title": "Task"}, ("acceptance", "blocker")),
            "screening": (
                {
                    "id": "screening-one",
                    "paper_id": "paper-one",
                    "state": "included",
                    "reason": "Relevant",
                    "recorded_at": "2026-08-11T00:00:00Z",
                },
                ("reviewer",),
            ),
        }
        for kind, (base, fields) in fixtures.items():
            for field in fields:
                with self.subTest(kind=kind, field=field, valid=True):
                    valid = copy.deepcopy(base)
                    valid[field] = "value"
                    self.assert_both_accept(kind, valid)
                with self.subTest(kind=kind, field=field, valid=False):
                    invalid = copy.deepcopy(base)
                    invalid[field] = []
                    self.assert_both_reject(kind, invalid)

    def test_required_text_fields_reject_whitespace_in_runtime_and_schema(self) -> None:
        fixtures: dict[str, tuple[dict[str, object], tuple[str, ...]]] = {
            "paper": (
                {"id": "paper-one", "title": "Paper", "authors": ["Author"], "year": 2026},
                ("title",),
            ),
            "claim": (
                {
                    "id": "claim-one",
                    "paper_id": "paper-one",
                    "statement": "Claim",
                    "evidence_locator": "Page 1",
                },
                ("statement", "evidence_locator"),
            ),
            "experiment": (
                {
                    "id": "experiment-one",
                    "paper_id": "paper-one",
                    "name": "Experiment",
                    "protocol_summary": "Protocol",
                },
                ("name", "protocol_summary"),
            ),
            "resource": (
                {"id": "resource-one", "name": "Resource", "kind": "code"},
                ("name",),
            ),
            "task": ({"id": "task-one", "title": "Task"}, ("title",)),
            "screening": (
                {
                    "id": "screening-one",
                    "paper_id": "paper-one",
                    "state": "included",
                    "reason": "Relevant",
                    "recorded_at": "2026-08-11T00:00:00Z",
                },
                ("reason", "recorded_at"),
            ),
        }
        for kind, (base, fields) in fixtures.items():
            for field in fields:
                with self.subTest(kind=kind, field=field):
                    invalid = copy.deepcopy(base)
                    invalid[field] = " \t"
                    self.assert_both_reject(kind, invalid)

        blank_author = {"id": "paper-one", "title": "Paper", "authors": [" "], "year": 2026}
        self.assert_both_reject("paper", blank_author)

    def test_json_schema_integer_year_is_normalized_by_runtime(self) -> None:
        paper: dict[str, object] = {
            "id": "paper-one",
            "title": "Paper",
            "authors": ["Author"],
            "year": 2025.0,
        }
        cloned = copy.deepcopy(paper)
        self.assertIs(validate("paper", cloned), cloned)
        self.assertEqual(cloned["year"], 2025)
        self.assertEqual(list(Draft202012Validator(load_schema("paper")).iter_errors(paper)), [])

    def test_every_published_schema_has_the_portable_id_budget(self) -> None:
        for path in sorted((ROOT / "schemas").glob("*.schema.json")):
            with self.subTest(schema=path.name):
                schema = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(schema["$defs"]["id"]["maxLength"], 200)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common import full_ratings, make_workspace

from reproweave.errors import ValidationError
from reproweave.triage import build_replication_triage, parse_resource_overrides


def add_candidate_data(workspace, *, availability: str = "available", state: str = "ready"):
    workspace.add(
        "resource",
        {
            "id": "paper-data",
            "name": "Paper data",
            "kind": "dataset",
            "availability": availability,
        },
    )
    workspace.add(
        "experiment",
        {
            "id": "paper-run",
            "paper_id": "paper-one",
            "name": "Paper run",
            "protocol_summary": "Run the documented experiment.",
            "resource_ids": ["paper-data"],
        },
    )
    workspace.add(
        "assessment",
        {
            "id": "assessment-one",
            "paper_id": "paper-one",
            "ratings": full_ratings(),
        },
    )
    workspace.add(
        "task",
        {
            "id": "run-paper",
            "title": "Run paper",
            "paper_ids": ["paper-one"],
            "state": state,
            "estimate_hours": 5,
        },
    )


class TriageTests(unittest.TestCase):
    def test_run_now_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            add_candidate_data(workspace)
            result = build_replication_triage(workspace)
            self.assertEqual(result["candidates"][0]["status"], "run_now")
            self.assertEqual(result["summary"]["run_now_ids"], ["paper-one"])

    def test_unavailable_resource_is_hard_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            add_candidate_data(workspace, availability="unavailable")
            candidate = build_replication_triage(workspace)["candidates"][0]
            self.assertEqual(candidate["status"], "evidence_first")
            self.assertEqual(candidate["unresolved_resource_ids"], ["paper-data"])

    def test_override_changes_scenario_without_mutating_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            add_candidate_data(workspace, availability="unavailable")
            candidate = build_replication_triage(workspace, {"paper-data": "available"})[
                "candidates"
            ][0]
            self.assertEqual(candidate["status"], "run_now")
            self.assertEqual(
                workspace.index("resource")["paper-data"]["availability"], "unavailable"
            )

    def test_unknown_override_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            with self.assertRaises(ValidationError):
                build_replication_triage(workspace, {"missing-data": "available"})

    def test_missing_plan_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            candidate = build_replication_triage(workspace)["candidates"][0]
            self.assertEqual(candidate["status"], "needs_planning")

    def test_parser_accepts_repeatable_overrides(self) -> None:
        self.assertEqual(
            parse_resource_overrides(["data=available", "board=partial"]),
            {"data": "available", "board": "partial"},
        )

    def test_parser_rejects_invalid_override(self) -> None:
        with self.assertRaises(ValidationError):
            parse_resource_overrides(["data=reachable"])


if __name__ == "__main__":
    unittest.main()

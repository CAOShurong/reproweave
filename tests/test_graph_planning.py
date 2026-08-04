from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common import full_ratings, make_workspace

from reproweave.errors import CycleError
from reproweave.graph import build_evidence_graph, topological_tasks
from reproweave.planning import build_replication_plan, readiness_backlog


class GraphPlanningTests(unittest.TestCase):
    def test_topological_order(self) -> None:
        tasks = [
            {"id": "second", "depends_on": ["first"]},
            {"id": "first", "depends_on": []},
        ]
        self.assertEqual([item["id"] for item in topological_tasks(tasks)], ["first", "second"])

    def test_cycle(self) -> None:
        tasks = [
            {"id": "one", "depends_on": ["two"]},
            {"id": "two", "depends_on": ["one"]},
        ]
        with self.assertRaises(CycleError):
            topological_tasks(tasks)

    def test_unknown_dependency_ignored_by_sort(self) -> None:
        tasks = [{"id": "one", "depends_on": ["outside"]}]
        self.assertEqual(topological_tasks(tasks)[0]["id"], "one")

    def test_graph_paper_node(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            graph = build_evidence_graph(workspace)
            self.assertEqual(graph["nodes"][0]["kind"], "paper")

    def test_graph_claim_edge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add(
                "claim",
                {
                    "id": "claim-one",
                    "paper_id": "paper-one",
                    "statement": "A claim.",
                    "evidence_locator": "p. 1",
                },
            )
            graph = build_evidence_graph(workspace)
            self.assertIn(
                {"source": "paper-one", "target": "claim-one", "type": "reports"},
                graph["edges"],
            )

    def test_plan_waves(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add(
                "task",
                {"id": "first", "title": "First", "depends_on": [], "estimate_hours": 2},
            )
            workspace.add(
                "task",
                {
                    "id": "second",
                    "title": "Second",
                    "depends_on": ["first"],
                    "estimate_hours": 3,
                },
            )
            plan = build_replication_plan(workspace)
            self.assertEqual(len(plan["waves"]), 2)
            self.assertEqual(plan["summary"]["total_effort_hours"], 5)

    def test_plan_parallel_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            for identifier, hours in (("one", 2), ("two", 4)):
                workspace.add(
                    "task",
                    {"id": identifier, "title": identifier, "estimate_hours": hours},
                )
            self.assertEqual(
                build_replication_plan(workspace)["summary"]["ideal_parallel_hours"], 4
            )

    def test_backlog(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            ratings = full_ratings()
            ratings["data"] = {"rating": "unknown", "evidence": "Not found."}
            workspace.add(
                "assessment",
                {"id": "assessment-one", "paper_id": "paper-one", "ratings": ratings},
            )
            backlog = readiness_backlog(workspace)
            self.assertEqual(backlog[0]["dimension"], "data")


if __name__ == "__main__":
    unittest.main()

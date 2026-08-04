from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common import make_workspace

from reproweave.errors import ValidationError
from reproweave.workspace import Workspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_create_layout(self) -> None:
        workspace = Workspace.create(self.root / "w", title="T", research_question="Q?")
        self.assertTrue(workspace.manifest_path.exists())
        self.assertTrue((workspace.root / "papers").is_dir())

    def test_create_twice_fails(self) -> None:
        Workspace.create(self.root / "w", title="T", research_question="Q?")
        with self.assertRaises(ValidationError):
            Workspace.create(self.root / "w", title="T", research_question="Q?")

    def test_manifest(self) -> None:
        workspace = Workspace.create(self.root / "w", title="Title", research_question="Why?")
        self.assertEqual(workspace.manifest()["title"], "Title")

    def test_add_and_get(self) -> None:
        workspace = make_workspace(self.root / "w")
        self.assertEqual(workspace.get("paper", "paper-one")["title"], "Paper One")

    def test_duplicate_add_fails(self) -> None:
        workspace = make_workspace(self.root / "w")
        with self.assertRaises(ValidationError):
            workspace.add(
                "paper",
                {"id": "paper-one", "title": "Again", "authors": ["A"], "year": 2025},
            )

    def test_replace(self) -> None:
        workspace = make_workspace(self.root / "w")
        workspace.add(
            "paper",
            {"id": "paper-one", "title": "Again", "authors": ["A"], "year": 2025},
            replace=True,
        )
        self.assertEqual(workspace.get("paper", "paper-one")["title"], "Again")

    def test_all_is_sorted(self) -> None:
        workspace = make_workspace(self.root / "w")
        workspace.add(
            "paper",
            {"id": "another", "title": "Another", "authors": ["A"], "year": 2024},
        )
        self.assertEqual([item["id"] for item in workspace.all("paper")], ["another", "paper-one"])

    def test_counts(self) -> None:
        workspace = make_workspace(self.root / "w")
        self.assertEqual(workspace.counts()["paper"], 1)
        self.assertEqual(workspace.counts()["claim"], 0)

    def test_invalid_workspace(self) -> None:
        with self.assertRaises(ValidationError):
            Workspace(self.root / "none").require()

    def test_path_for(self) -> None:
        workspace = make_workspace(self.root / "w")
        self.assertEqual(workspace.path_for("claim", "claim-one").name, "claim-one.json")


if __name__ == "__main__":
    unittest.main()

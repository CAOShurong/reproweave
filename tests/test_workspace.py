from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from common import make_workspace

from reproweave.errors import ValidationError
from reproweave.store import write_json
from reproweave.util import filesystem_path
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

    def test_add_maximum_length_id_uses_a_short_atomic_temp_name(self) -> None:
        workspace = make_workspace(self.root / ("d" * 64) / "w")
        artifact_id = "a" + "1" * 199
        path = workspace.add("task", {"id": artifact_id, "title": "Long identifier"})
        self.assertGreater(len(str(path)), 260)
        self.assertEqual(path.name, f"{artifact_id}.json")
        self.assertEqual(workspace.get("task", artifact_id)["id"], artifact_id)
        with self.assertRaisesRegex(ValidationError, "already exists"):
            workspace.add("task", {"id": artifact_id, "title": "Duplicate"})
        workspace.add(
            "task",
            {"id": artifact_id, "title": "Replacement"},
            replace=True,
        )
        self.assertEqual(workspace.get("task", artifact_id)["title"], "Replacement")
        self.assertEqual(workspace.all("task")[0]["id"], artifact_id)
        os.unlink(filesystem_path(path))

    def test_duplicate_add_fails(self) -> None:
        workspace = make_workspace(self.root / "w")
        with self.assertRaises(ValidationError):
            workspace.add(
                "paper",
                {"id": "paper-one", "title": "Again", "authors": ["A"], "year": 2025},
            )

    def test_add_rejects_id_already_used_by_another_artifact_kind(self) -> None:
        workspace = make_workspace(self.root / "w")
        with self.assertRaisesRegex(ValidationError, "already used"):
            workspace.add(
                "task",
                {"id": "paper-one", "title": "Must not shadow the paper"},
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

    def test_all_rejects_filename_id_mismatch(self) -> None:
        workspace = make_workspace(self.root / "w")
        write_json(
            workspace.root / "papers" / "wrong-name.json",
            {"id": "paper-two", "title": "Paper Two", "authors": ["B"], "year": 2024},
        )
        with self.assertRaisesRegex(ValidationError, "filename"):
            workspace.all("paper")

    def test_uppercase_json_extension_is_rejected_on_every_platform(self) -> None:
        workspace = make_workspace(self.root / "w")
        write_json(
            workspace.root / "papers" / "paper-two.JSON",
            {"id": "paper-two", "title": "Paper Two", "authors": ["B"], "year": 2024},
        )
        with self.assertRaisesRegex(ValidationError, "lowercase .json"):
            workspace.all("paper")

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

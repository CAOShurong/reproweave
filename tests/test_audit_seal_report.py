from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common import make_workspace

from reproweave.audit import audit_workspace
from reproweave.demo import create_demo
from reproweave.report import build_report
from reproweave.seal import build_seal, verify_seal, write_seal


class AuditSealReportTests(unittest.TestCase):
    def test_minimal_workspace_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            self.assertEqual(audit_workspace(workspace)["status"], "pass")

    def test_missing_paper_reference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add(
                "claim",
                {
                    "id": "claim-one",
                    "paper_id": "not-there",
                    "statement": "Claim.",
                    "evidence_locator": "p. 1",
                },
            )
            result = audit_workspace(workspace)
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["issues"][0]["code"], "claim.paper_missing")

    def test_included_unassessed_warns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add(
                "screening",
                {
                    "id": "screen-one",
                    "paper_id": "paper-one",
                    "state": "included",
                    "reason": "Eligible.",
                    "recorded_at": "2025-01-01T00:00:00Z",
                },
            )
            result = audit_workspace(workspace)
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["counts"]["warnings"], 1)

    def test_seal_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            self.assertEqual(build_seal(workspace)["root"], build_seal(workspace)["root"])

    def test_verify_seal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            write_seal(workspace)
            self.assertEqual(verify_seal(workspace)["status"], "verified")

    def test_changed_seal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            write_seal(workspace)
            paper = workspace.get("paper", "paper-one")
            paper["title"] = "Changed"
            workspace.add("paper", paper, replace=True)
            self.assertEqual(verify_seal(workspace)["status"], "changed")

    def test_report_contains_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            destination = build_report(workspace, Path(directory) / "report.html")
            text = destination.read_text(encoding="utf-8")
            self.assertIn("not scientific quality", text)

    def test_report_escapes_title(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            manifest = workspace.manifest()
            manifest["title"] = "<unsafe>"
            from reproweave.store import write_json

            write_json(workspace.manifest_path, manifest)
            text = build_report(workspace, Path(directory) / "r.html").read_text(encoding="utf-8")
            self.assertIn("&lt;unsafe&gt;", text)

    def test_demo_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = create_demo(Path(directory) / "demo")
            self.assertEqual(workspace.counts()["claim"], 10)
            self.assertEqual(workspace.counts()["task"], 12)

    def test_demo_is_audit_clean(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = create_demo(Path(directory) / "demo")
            self.assertEqual(audit_workspace(workspace)["status"], "pass")

    def test_demo_refuses_nonempty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "demo"
            root.mkdir()
            (root / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                create_demo(root)


if __name__ == "__main__":
    unittest.main()

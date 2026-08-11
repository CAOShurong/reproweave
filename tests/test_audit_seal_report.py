from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from common import make_workspace

from reproweave.audit import audit_workspace
from reproweave.demo import create_demo
from reproweave.report import build_report
from reproweave.seal import build_seal, verify_seal, write_seal
from reproweave.store import write_json
from reproweave.workspace import Workspace


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

    def test_audit_reports_bad_json_without_hiding_valid_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            (workspace.root / "papers" / "broken.json").write_text("{", encoding="utf-8")
            result = audit_workspace(workspace)
            self.assertEqual(result["status"], "fail")
            self.assertIn("paper.invalid", {item["code"] for item in result["issues"]})
            self.assertEqual(result["counts"]["paper"], 1)

    def test_audit_reports_filename_mismatch_and_duplicate_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            value = {"id": "paper-shadow", "title": "Shadow", "authors": ["B"], "year": 2024}
            write_json(workspace.root / "papers" / "alias-one.json", value)
            write_json(workspace.root / "papers" / "alias-two.json", value)
            result = audit_workspace(workspace)
            codes = {item["code"] for item in result["issues"]}
            self.assertEqual(result["status"], "fail")
            self.assertIn("artifact.filename_mismatch", codes)
            self.assertIn("artifact.id_duplicate", codes)

    def test_audit_reports_workspace_wide_id_collision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            workspace.add(
                "claim",
                {
                    "id": "shared-id",
                    "paper_id": "paper-one",
                    "statement": "A bounded claim.",
                    "evidence_locator": "Figure 1",
                },
            )
            write_json(
                workspace.root / "tasks" / "shared-id.json",
                {"id": "shared-id", "title": "Do the work"},
            )
            result = audit_workspace(workspace)
            self.assertEqual(result["status"], "fail")
            self.assertIn("artifact.id_duplicate", {item["code"] for item in result["issues"]})

    def test_audit_accumulates_multiple_bad_files_with_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            (workspace.root / "papers" / "broken.json").write_text("{", encoding="utf-8")
            (workspace.root / "tasks" / "invalid.json").write_text("[]", encoding="utf-8")
            result = audit_workspace(workspace)
            artifacts = {item["artifact"] for item in result["issues"]}
            self.assertEqual(result["status"], "fail")
            self.assertIn("papers/broken.json", artifacts)
            self.assertIn("tasks/invalid.json", artifacts)
            self.assertEqual(result["counts"]["paper"], 1)

    def test_audit_handles_non_string_enum_values_as_structured_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            from common import full_ratings

            write_json(
                workspace.root / "claims" / "bad-type.json",
                {
                    "id": "bad-type",
                    "paper_id": "paper-one",
                    "statement": "Claim.",
                    "evidence_locator": "Figure 1",
                    "type": [],
                },
            )
            write_json(
                workspace.root / "claims" / "bad-confidence.json",
                {
                    "id": "bad-confidence",
                    "paper_id": "paper-one",
                    "statement": "Claim.",
                    "evidence_locator": "Figure 2",
                    "confidence": {},
                },
            )
            write_json(
                workspace.root / "resources" / "bad-availability.json",
                {
                    "id": "bad-availability",
                    "name": "Bad resource",
                    "kind": "data",
                    "availability": [],
                },
            )
            invalid_kind = {
                "id": "bad-kind",
                "paper_id": "paper-one",
                "kind": {},
                "ratings": full_ratings(),
            }
            write_json(workspace.root / "assessments" / "bad-kind.json", invalid_kind)
            invalid_rating = full_ratings()
            invalid_rating["method"]["rating"] = []
            write_json(
                workspace.root / "assessments" / "bad-rating.json",
                {
                    "id": "bad-rating",
                    "paper_id": "paper-one",
                    "ratings": invalid_rating,
                },
            )
            result = audit_workspace(workspace)
            artifacts = {item["artifact"] for item in result["issues"]}
            self.assertEqual(result["status"], "fail")
            self.assertTrue(
                {
                    "claims/bad-type.json",
                    "claims/bad-confidence.json",
                    "resources/bad-availability.json",
                    "assessments/bad-kind.json",
                    "assessments/bad-rating.json",
                }.issubset(artifacts)
            )

    def test_audit_rejects_effort_beyond_the_published_numeric_budget(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            write_json(
                workspace.root / "tasks" / "large-estimate.json",
                {
                    "id": "large-estimate",
                    "title": "Impractically large integer",
                    "estimate_hours": 10**400,
                },
            )
            result = audit_workspace(workspace)
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["counts"]["task"], 0)
            self.assertEqual(result["issues"][0]["code"], "task.invalid")

    def test_audit_rejects_overflowed_float_in_manifest_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            text = workspace.manifest_path.read_text(encoding="utf-8").rstrip()
            workspace.manifest_path.write_text(
                text[:-1] + ', "x-overflow": 1e9999}\n',
                encoding="utf-8",
                newline="\n",
            )
            result = audit_workspace(workspace)
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["issues"][0]["code"], "manifest.invalid")

    def test_audit_rejects_explicit_null_optional_id_lists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            write_json(
                workspace.root / "claims" / "null-experiments.json",
                {
                    "id": "null-experiments",
                    "paper_id": "paper-one",
                    "statement": "Claim.",
                    "evidence_locator": "Figure 1",
                    "experiment_ids": None,
                },
            )
            for field in ("resource_ids", "metric_ids", "baseline_ids"):
                artifact_id = f"null-{field.replace('_', '-')}"
                write_json(
                    workspace.root / "experiments" / f"{artifact_id}.json",
                    {
                        "id": artifact_id,
                        "paper_id": "paper-one",
                        "name": "Experiment",
                        "protocol_summary": "Protocol.",
                        field: None,
                    },
                )
            for field in ("depends_on", "paper_ids"):
                artifact_id = f"null-{field.replace('_', '-')}"
                write_json(
                    workspace.root / "tasks" / f"{artifact_id}.json",
                    {"id": artifact_id, "title": "Task", field: None},
                )
            result = audit_workspace(workspace)
            self.assertEqual(result["status"], "fail")
            self.assertEqual(
                len([item for item in result["issues"] if item["code"].endswith(".invalid")]),
                6,
            )

    def test_audit_rejects_ambiguous_or_unencodable_json_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            (workspace.root / "papers" / "bad-utf8.json").write_bytes(b"\xff")
            (workspace.root / "papers" / "duplicate-key.json").write_text(
                '{"id":"duplicate-key","id":"paper-one","title":"First",'
                '"title":"Second","authors":["A"],"year":2025}',
                encoding="utf-8",
            )
            (workspace.root / "papers" / "lone-surrogate.json").write_text(
                r'{"id":"lone-surrogate","title":"\ud800","authors":["A"],"year":2025}',
                encoding="utf-8",
            )
            result = audit_workspace(workspace)
            artifacts = {item["artifact"] for item in result["issues"]}
            self.assertEqual(result["status"], "fail")
            self.assertTrue(
                {
                    "papers/bad-utf8.json",
                    "papers/duplicate-key.json",
                    "papers/lone-surrogate.json",
                }.issubset(artifacts)
            )
            self.assertEqual(result["counts"]["paper"], 1)

    def test_audit_paths_deep_and_huge_json_failures_without_stopping(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            (workspace.root / "papers" / "deep.json").write_text(
                '{"id":"deep","title":"Deep","authors":["A"],"year":2025,"x":'
                + "[" * 1200
                + "0"
                + "]" * 1200
                + "}",
                encoding="utf-8",
            )
            (workspace.root / "papers" / "huge-number.json").write_text(
                '{"id":"huge-number","title":"Huge","authors":["A"],"year":2025,"x":'
                + "1" * 5000
                + "}",
                encoding="utf-8",
            )
            (workspace.root / "papers" / "bad-directory.json").mkdir()
            write_json(
                workspace.root / "papers" / "paper-two.JSON",
                {"id": "paper-two", "title": "Paper Two", "authors": ["B"], "year": 2024},
            )
            result = audit_workspace(workspace)
            issues = {item["artifact"]: item["code"] for item in result["issues"]}
            self.assertEqual(result["status"], "fail")
            self.assertEqual(issues["papers/deep.json"], "paper.invalid")
            self.assertEqual(issues["papers/huge-number.json"], "paper.invalid")
            self.assertEqual(issues["papers/bad-directory.json"], "paper.invalid")
            self.assertEqual(
                issues["papers/paper-two.JSON"],
                "artifact.filename_extension",
            )
            self.assertEqual(result["counts"]["paper"], 1)

    def test_audit_reports_invalid_artifact_directory_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace.create(
                Path(directory) / "w", title="Review", research_question="Question?"
            )
            papers = workspace.root / "papers"
            papers.rmdir()
            papers.write_text("not a directory", encoding="utf-8")
            (workspace.root / "claims" / "bad.json").write_text("{", encoding="utf-8")
            result = audit_workspace(workspace)
            issues = {(item["artifact"], item["code"]) for item in result["issues"]}
            self.assertEqual(result["status"], "fail")
            self.assertIn(("papers", "workspace.directory_invalid"), issues)
            self.assertIn(("claims/bad.json", "claim.invalid"), issues)

    def test_audit_reports_unreadable_artifact_directory_and_continues(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            (workspace.root / "claims" / "bad.json").write_text("{", encoding="utf-8")
            original_iterdir = Path.iterdir

            def flaky_iterdir(path: Path):
                if path == workspace.root / "papers":
                    raise PermissionError("synthetic enumeration failure")
                return original_iterdir(path)

            with mock.patch.object(Path, "iterdir", flaky_iterdir):
                result = audit_workspace(workspace)
            issues = {(item["artifact"], item["code"]) for item in result["issues"]}
            self.assertEqual(result["status"], "fail")
            self.assertIn(("papers", "workspace.directory_invalid"), issues)
            self.assertIn(("claims/bad.json", "claim.invalid"), issues)

    def test_audit_rejects_unresolved_assessment_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = make_workspace(Path(directory) / "w")
            from common import full_ratings

            workspace.add(
                "assessment",
                {"id": "review-one", "paper_id": "paper-one", "ratings": full_ratings("yes")},
            )
            workspace.add(
                "assessment",
                {"id": "review-two", "paper_id": "paper-one", "ratings": full_ratings("no")},
            )
            result = audit_workspace(workspace)
            self.assertEqual(result["status"], "fail")
            self.assertIn("assessment.conflict", {item["code"] for item in result["issues"]})

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
            self.assertIn("Replication candidate triage", text)
            self.assertIn("Reviewer agreement", text)
            self.assertIn('name="generator" content="ReproWeave 0.3.0"', text)

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

    def test_demo_seal_is_byte_stable_across_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = create_demo(Path(directory) / "first")
            second = create_demo(Path(directory) / "second")
            self.assertEqual(
                (first.root / "reproweave-seal.json").read_bytes(),
                (second.root / "reproweave-seal.json").read_bytes(),
            )

    def test_demo_refuses_nonempty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "demo"
            root.mkdir()
            (root / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                create_demo(root)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import contextlib
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from common import make_workspace

from reproweave.cli import _parser, run
from reproweave.duplicates import (
    build_duplicate_report,
    duplicate_report_csv,
    duplicate_report_markdown,
    normalize_doi,
)
from reproweave.errors import ValidationError


def paper(
    paper_id: str,
    *,
    title: str = "A Study",
    year: int = 2025,
    author: str = "Ada Lovelace",
    doi: str = "",
) -> dict[str, object]:
    return {
        "id": paper_id,
        "title": title,
        "authors": [author],
        "year": year,
        "doi": doi,
    }


class DuplicateReportTests(unittest.TestCase):
    def test_doi_wrappers_normalize_conservatively(self) -> None:
        expected = "10.5555/example.test"
        for value in (
            "10.5555/Example.Test",
            "doi: 10.5555/example.test",
            "https://doi.org/10.5555/EXAMPLE.TEST",
            "http://dx.doi.org/10.5555/example.test",
        ):
            with self.subTest(value=value):
                self.assertEqual(normalize_doi(value), expected)

    def test_report_is_input_order_independent_and_does_not_rewrite_source(self) -> None:
        left = paper("left", doi="https://doi.org/10.5555/Case.Test")
        right = paper("right", doi="doi:10.5555/case.test", title="Different title")
        original = json.dumps([left, right], sort_keys=True)
        forward = build_duplicate_report([left, right])
        reverse = build_duplicate_report([right, left])
        self.assertEqual(forward, reverse)
        self.assertEqual(json.dumps([left, right], sort_keys=True), original)
        self.assertEqual(forward["candidate_group_count"], 1)
        self.assertEqual(forward["candidates"][0]["confidence"], "exact")

    def test_candidate_id_binds_normalized_evidence_but_not_doi_wrappers(self) -> None:
        first = build_duplicate_report(
            [paper("left", doi="10.5555/old"), paper("right", doi="doi:10.5555/OLD")]
        )["candidates"][0]["candidate_id"]
        wrapped = build_duplicate_report(
            [
                paper("left", doi="https://doi.org/10.5555/OLD"),
                paper("right", doi="10.5555/old"),
            ]
        )["candidates"][0]["candidate_id"]
        changed = build_duplicate_report(
            [paper("left", doi="10.5555/new"), paper("right", doi="doi:10.5555/NEW")]
        )["candidates"][0]["candidate_id"]
        self.assertEqual(first, wrapped)
        self.assertNotEqual(first, changed)

    def test_same_doi_and_title_is_still_exact(self) -> None:
        candidate = build_duplicate_report(
            [paper("left", doi="10.5555/same"), paper("right", doi="10.5555/same")]
        )["candidates"][0]
        self.assertEqual(candidate["reasons"], ["same_doi", "same_title_year_author"])
        self.assertEqual(candidate["confidence"], "exact")

    def test_possible_title_candidate_supports_nfkc_and_one_year_window(self) -> None:
        report = build_duplicate_report(
            [
                paper("wide", title="Ａ Reproducible Study", year=2024),
                paper("plain", title="a   reproducible study", year=2025),
            ]
        )
        self.assertEqual(report["candidates"][0]["reasons"], ["same_title_year_author"])

    def test_csv_and_markdown_escape_untrusted_fields(self) -> None:
        report = build_duplicate_report(
            [
                paper("one", title="=2+3 <script> | title\nline", doi="10.1/same"),
                paper("two", title="Other", doi="10.1/same"),
            ]
        )
        rows = list(csv.DictReader(io.StringIO(duplicate_report_csv(report))))
        self.assertEqual([row["paper_id"] for row in rows], ["one", "two"])
        self.assertEqual(rows[0]["title"], "'=2+3 <script> | title\nline")
        markdown = duplicate_report_markdown(report)
        self.assertIn("=2+3 &lt;script&gt; \\| title line", markdown)


class ImportPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = make_workspace(self.root / "workspace")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def paper_files(self) -> dict[str, bytes]:
        return {
            path.name: path.read_bytes()
            for path in sorted((self.workspace.root / "papers").glob("*.json"))
        }

    def test_late_existing_id_collision_leaves_zero_batch_files(self) -> None:
        before = self.paper_files()
        with self.assertRaisesRegex(ValidationError, "incoming batch was not written"):
            self.workspace.add_many(
                "paper",
                [paper("new-record"), paper("paper-one", title="Collision")],
            )
        self.assertEqual(self.paper_files(), before)

    def test_batch_doi_candidate_blocks_then_accepts_exact_candidate(self) -> None:
        incoming = [
            paper("doi-a", doi="https://doi.org/10.5555/Duplicate.Test"),
            paper("doi-b", title="Another", doi="doi:10.5555/duplicate.test"),
        ]
        plan = self.workspace.preflight_many("paper", incoming)
        self.assertFalse(plan.ready)
        self.assertFalse((self.workspace.root / "papers" / "doi-a.json").exists())
        candidate_id = plan.candidates[0]["candidate_id"]
        paths = self.workspace.add_many("paper", incoming, accepted_candidate_ids=[candidate_id])
        self.assertEqual([path.stem for path in paths], ["doi-a", "doi-b"])
        self.assertEqual(self.workspace.get("paper", "doi-a")["doi"], incoming[0]["doi"])
        self.assertEqual(
            build_duplicate_report(self.workspace.all("paper"))["candidates"][0]["candidate_id"],
            candidate_id,
        )

    def test_changed_duplicate_evidence_rejects_stale_acceptance(self) -> None:
        old = [
            paper("stale-a", doi="10.5555/old"),
            paper("stale-b", title="Old B", doi="doi:10.5555/OLD"),
        ]
        stale_id = self.workspace.preflight_many("paper", old).candidates[0]["candidate_id"]
        changed = [
            paper("stale-a", doi="10.5555/new"),
            paper("stale-b", title="Old B", doi="doi:10.5555/NEW"),
        ]
        with self.assertRaisesRegex(ValidationError, "absent from this preflight"):
            self.workspace.add_many("paper", changed, accepted_candidate_ids=[stale_id])
        self.assertFalse((self.workspace.root / "papers" / "stale-a.json").exists())

    def test_single_add_uses_duplicate_policy_and_explicit_acceptance(self) -> None:
        incoming = paper(
            "paper-copy",
            title="Paper One",
            year=2025,
            author="A. Author",
        )
        with self.assertRaisesRegex(ValidationError, "explicit acceptance"):
            self.workspace.add("paper", incoming)
        plan = self.workspace.preflight_many("paper", [incoming])
        candidate_id = plan.candidates[0]["candidate_id"]
        path = self.workspace.add("paper", incoming, accepted_candidate_ids=[candidate_id])
        self.assertEqual(path.stem, "paper-copy")

    def test_cli_add_paper_cannot_bypass_duplicate_policy(self) -> None:
        source = self.root / "paper.json"
        source.write_text(
            json.dumps(
                paper(
                    "paper-copy",
                    title="Paper One",
                    year=2025,
                    author="A. Author",
                )
            ),
            encoding="utf-8",
        )
        arguments = _parser().parse_args(
            ["add", "paper", str(source), "--workspace", str(self.workspace.root)]
        )
        with self.assertRaisesRegex(ValidationError, "explicit acceptance"):
            run(arguments)

    def test_cross_kind_collision_and_serialization_failure_leave_zero_batch_files(self) -> None:
        before = {
            path.relative_to(self.workspace.root).as_posix(): path.read_bytes()
            for path in self.workspace.root.rglob("*")
            if path.is_file()
        }
        with self.assertRaisesRegex(ValidationError, "already used by paper"):
            self.workspace.add_many(
                "task",
                [
                    {"id": "new-task", "title": "New task"},
                    {"id": "paper-one", "title": "Cross-kind collision"},
                ],
            )
        self.assertEqual(
            {
                path.relative_to(self.workspace.root).as_posix(): path.read_bytes()
                for path in self.workspace.root.rglob("*")
                if path.is_file()
            },
            before,
        )
        with self.assertRaisesRegex(ValidationError, "cannot be serialized"):
            self.workspace.add_many(
                "paper",
                [paper("serializable"), {**paper("bad-json"), "extension": {"a-set"}}],
            )
        self.assertFalse((self.workspace.root / "papers" / "serializable.json").exists())

    def test_dry_run_report_is_stable_and_does_not_mutate_inputs(self) -> None:
        incoming = [paper("float-year", year=2025.0)]
        original = json.dumps(incoming, sort_keys=True)
        first = self.workspace.preflight_many("paper", incoming).report(dry_run=True)
        second = self.workspace.preflight_many("paper", incoming).report(dry_run=True)
        self.assertEqual(first, second)
        self.assertEqual(json.dumps(incoming, sort_keys=True), original)
        self.assertFalse((self.workspace.root / "papers" / "float-year.json").exists())

    def test_dry_run_report_is_independent_of_input_order(self) -> None:
        incoming = [
            paper("zeta", title="Zeta", author="Z", doi="10.5555/same"),
            paper("alpha", title="Alpha", author="A", doi="doi:10.5555/SAME"),
        ]
        forward = self.workspace.preflight_many("paper", incoming).report(dry_run=True)
        reverse = self.workspace.preflight_many("paper", list(reversed(incoming))).report(
            dry_run=True
        )
        self.assertEqual(forward, reverse)

    def test_mutated_or_stale_internal_plan_is_rejected(self) -> None:
        mutable_plan = self.workspace.preflight_many(
            "paper", [paper("mutable", title="Mutable", author="M")]
        )
        mutable_plan.artifacts[0]["id"] = "changed"
        with self.assertRaisesRegex(ValidationError, "changed after preflight"):
            self.workspace._commit_many(mutable_plan)
        self.assertFalse((self.workspace.root / "papers" / "changed.json").exists())

        stale_plan = self.workspace.preflight_many(
            "paper", [paper("victim", title="Incoming", author="I")]
        )
        stored = paper("victim", title="Stored", author="S")
        self.workspace.add("paper", stored)
        before = (self.workspace.root / "papers" / "victim.json").read_bytes()
        with self.assertRaisesRegex(ValidationError, "already exists"):
            self.workspace._commit_many(stale_plan)
        self.assertEqual((self.workspace.root / "papers" / "victim.json").read_bytes(), before)

    def test_replace_excludes_the_replaced_record_but_not_a_third_paper(self) -> None:
        self.workspace.add(
            "paper",
            paper("third", title="Another", doi="10.5555/conflict"),
        )
        replacement = paper("paper-one", doi="doi:10.5555/conflict")
        plan = self.workspace.preflight_many("paper", [replacement], replace=True)
        self.assertFalse(plan.ready)
        self.assertEqual(plan.candidates[0]["paper_ids"], ["paper-one", "third"])

    def test_cli_dry_run_and_blocked_candidate_are_machine_readable(self) -> None:
        ready_source = self.root / "ready.bib"
        ready_source.write_text(
            "@article{Ready, title={Ready}, author={A}, year={2025}}",
            encoding="utf-8",
        )
        arguments = _parser().parse_args(
            [
                "import",
                "bibtex",
                str(ready_source),
                "--workspace",
                str(self.workspace.root),
                "--dry-run",
            ]
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(run(arguments), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "ready")
        self.assertFalse((self.workspace.root / "papers" / "ready.json").exists())

        blocked_source = self.root / "blocked.bib"
        blocked_source.write_text(
            "@article{A, title={One}, author={A}, year={2025}, doi={10.1/x}}\n"
            "@article{B, title={Two}, author={B}, year={2024}, doi={https://doi.org/10.1/X}}",
            encoding="utf-8",
        )
        arguments = _parser().parse_args(
            [
                "import",
                "bibtex",
                str(blocked_source),
                "--workspace",
                str(self.workspace.root),
            ]
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(run(arguments), 5)
        report = json.loads(output.getvalue())
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["issues"][0]["code"], "duplicate_candidate")
        self.assertFalse((self.workspace.root / "papers" / "a.json").exists())

    def test_cli_dry_run_existing_id_error_is_machine_readable(self) -> None:
        source = self.root / "collision.bib"
        source.write_text(
            "@article{paper-one, title={Collision}, author={A}, year={2025}}",
            encoding="utf-8",
        )
        arguments = _parser().parse_args(
            [
                "import",
                "bibtex",
                str(source),
                "--workspace",
                str(self.workspace.root),
                "--dry-run",
            ]
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(run(arguments), 5)
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["paper_ids"], ["paper-one"])
        self.assertEqual(report["issues"][0]["code"], "preflight_error")
        self.assertEqual(stderr.getvalue(), "")

    def test_cli_dry_run_invalid_workspace_is_machine_readable(self) -> None:
        source = self.root / "ready-for-invalid-workspace.bib"
        source.write_text(
            "@article{ready, title={Ready}, author={A}, year={2025}}",
            encoding="utf-8",
        )
        invalid_workspace = self.root / "not-a-workspace"
        invalid_workspace.mkdir()
        arguments = _parser().parse_args(
            [
                "import",
                "bibtex",
                str(source),
                "--workspace",
                str(invalid_workspace),
                "--dry-run",
            ]
        )
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(run(arguments), 5)
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["would_import"], 0)
        self.assertEqual(report["issues"][0]["code"], "preflight_error")


if __name__ == "__main__":
    unittest.main()

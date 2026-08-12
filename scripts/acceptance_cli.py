"""Exercise the built wheel through representative success and failure paths."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

DIMENSIONS = (
    "method",
    "data",
    "code",
    "environment",
    "metrics",
    "baselines",
    "compute",
    "results",
)


def ratings(value: str) -> dict[str, dict[str, str]]:
    return {
        dimension: {"rating": value, "evidence": "Synthetic acceptance evidence."}
        for dimension in DIMENSIONS
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def digest(value: dict[str, Any]) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def workspace_snapshot(root: Path) -> dict[str, str]:
    """Hash every workspace file so no-side-effect paths are observable."""
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def run(command: list[str], expected: int = 0) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "PYTHONUTF8": "1"}
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        check=False,
    )
    if result.returncode != expected:
        raise AssertionError(
            f"expected exit {expected}, got {result.returncode}: {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel-dir", required=True, type=Path)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()

    wheels = sorted(args.wheel_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise AssertionError(f"expected one wheel in {args.wheel_dir}, found {len(wheels)}")
    if args.root.exists():
        raise AssertionError(f"acceptance root already exists: {args.root}")
    args.root.mkdir(parents=True)

    environment = args.root / "venv"
    run([sys.executable, "-m", "venv", str(environment)])
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    entrypoint = environment / ("Scripts/reproweave.exe" if os.name == "nt" else "bin/reproweave")
    run([str(python), "-m", "pip", "install", "--no-deps", str(wheels[0])])
    cli = [str(python), "-m", "reproweave"]
    version = run([*cli, "--version"]).stdout.strip()
    if version != "reproweave 0.4.2":
        raise AssertionError(f"unexpected installed version: {version}")
    if run([str(entrypoint), "--version"]).stdout.strip() != version:
        raise AssertionError("console script version differs from python -m entry point")
    entrypoint_workspace = args.root / "entrypoint-review"
    run([str(entrypoint), "demo", str(entrypoint_workspace)])
    run([str(entrypoint), "audit", "--workspace", str(entrypoint_workspace)])

    import_workspace = args.root / "import-review"
    run(
        [
            *cli,
            "init",
            str(import_workspace),
            "--title",
            "Import acceptance",
            "--question",
            "Can imports preserve review evidence?",
        ]
    )

    existing_bib = args.root / "existing.bib"
    existing_bib.write_text(
        "@article{Existing, title={Existing record}, author={A}, year={2024}, "
        "doi={10.5555/existing}}\n",
        encoding="utf-8",
        newline="\n",
    )
    run([*cli, "import", "bibtex", str(existing_bib), "--workspace", str(import_workspace)])

    deep_workspace = args.root.joinpath(
        *(("segment-" + "x" * 36,) * 6),
        "deep-workspace-review",
    )
    if len(str(deep_workspace)) <= 260:
        raise AssertionError(
            f"deep workspace acceptance target is too short: {len(str(deep_workspace))}"
        )
    run(
        [
            *cli,
            "init",
            str(deep_workspace),
            "--title",
            "Unicode 研究 deep workspace",
            "--question",
            "Can the installed wheel complete a workflow beyond the Windows path limit?",
        ]
    )
    run([*cli, "import", "bibtex", str(existing_bib), "--workspace", str(deep_workspace)])
    run([*cli, "audit", "--workspace", str(deep_workspace)])
    run([*cli, "report", "--workspace", str(deep_workspace)])
    run([*cli, "seal", "--workspace", str(deep_workspace)])
    run([*cli, "verify", "--workspace", str(deep_workspace)])

    null_doi_csl = args.root / "null-doi.json"
    null_doi_csl.write_text(
        json.dumps(
            [
                {
                    "id": "null-doi-a",
                    "title": "Null DOI A",
                    "author": [{"literal": "A"}],
                    "issued": {"date-parts": [[2025]]},
                    "DOI": None,
                },
                {
                    "id": "null-doi-b",
                    "title": "Null DOI B",
                    "author": [{"literal": "B"}],
                    "issued": {"date-parts": [[2025]]},
                    "DOI": None,
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
        newline="\n",
    )
    run(
        [
            *cli,
            "import",
            "csl-json",
            str(null_doi_csl),
            "--workspace",
            str(import_workspace),
        ]
    )
    if json.loads(run([*cli, "duplicates", "--workspace", str(import_workspace)]).stdout)[
        "candidate_group_count"
    ]:
        raise AssertionError("null DOI values were treated as duplicate identifiers")

    malformed_date_parts = args.root / "malformed-date-parts.json"
    malformed_date_parts.write_text(
        '{"id":"bad-date","title":"Bad date","issued":{"date-parts":[{}]}}',
        encoding="utf-8",
        newline="\n",
    )
    malformed_date_result = run(
        [
            *cli,
            "import",
            "csl-json",
            str(malformed_date_parts),
            "--workspace",
            str(import_workspace),
            "--dry-run",
        ],
        5,
    )
    malformed_date_report = json.loads(malformed_date_result.stdout)
    if malformed_date_report["issues"][0]["code"] != "preflight_error":
        raise AssertionError("malformed CSL date did not return a structured preflight error")

    late_collision = args.root / "late-collision.bib"
    late_collision.write_text(
        "@article{NewRecord, title={New record}, author={B}, year={2025}}\n"
        "@article{Existing, title={Collision}, author={C}, year={2025}}\n",
        encoding="utf-8",
        newline="\n",
    )
    before_collision = workspace_snapshot(import_workspace)
    run(
        [*cli, "import", "bibtex", str(late_collision), "--workspace", str(import_workspace)],
        1,
    )
    if workspace_snapshot(import_workspace) != before_collision:
        raise AssertionError("preflightable late collision partially changed the workspace")
    collision_dry_run = run(
        [
            *cli,
            "import",
            "bibtex",
            str(late_collision),
            "--workspace",
            str(import_workspace),
            "--dry-run",
        ],
        5,
    )
    collision_report = json.loads(collision_dry_run.stdout)
    if collision_report["issues"][0]["code"] != "preflight_error":
        raise AssertionError("dry-run collision did not return a structured preflight error")

    invalid_utf8 = args.root / "invalid-utf8.json"
    invalid_utf8.write_bytes(b"\xff\xfe")
    invalid_utf8_result = run(
        [
            *cli,
            "import",
            "csl-json",
            str(invalid_utf8),
            "--workspace",
            str(import_workspace),
        ],
        1,
    )
    if "Traceback" in invalid_utf8_result.stderr or "cannot read CSL JSON source" not in (
        invalid_utf8_result.stderr
    ):
        raise AssertionError("invalid UTF-8 did not produce a controlled CLI error")

    single_duplicate = args.root / "single-duplicate.json"
    write_json(
        single_duplicate,
        {
            "id": "single-duplicate",
            "title": "Single duplicate",
            "authors": ["S"],
            "year": 2025,
            "doi": "https://doi.org/10.5555/EXISTING",
        },
    )
    before_single_add = workspace_snapshot(import_workspace)
    run(
        [
            *cli,
            "add",
            "paper",
            str(single_duplicate),
            "--workspace",
            str(import_workspace),
        ],
        1,
    )
    if workspace_snapshot(import_workspace) != before_single_add:
        raise AssertionError("single-paper add bypassed duplicate preflight")

    duplicate_bib = args.root / "duplicate-doi.bib"
    duplicate_bib.write_text(
        "@article{DoiA, title={=2+3 <b>First</b>}, author={D}, year={2025}, "
        "doi={https://doi.org/10.5555/Duplicate.Test}}\n"
        "@article{DoiB, title={Second title}, author={E}, year={2024}, "
        "doi={doi:10.5555/duplicate.test}}\n",
        encoding="utf-8",
        newline="\n",
    )
    duplicate_source_hash = hashlib.sha256(duplicate_bib.read_bytes()).hexdigest()
    before_duplicate = workspace_snapshot(import_workspace)
    blocked = run(
        [
            str(entrypoint),
            "import",
            "bibtex",
            str(duplicate_bib),
            "--workspace",
            str(import_workspace),
            "--dry-run",
        ],
        5,
    )
    blocked_report = json.loads(blocked.stdout)
    candidate_id = blocked_report["candidates"][0]["candidate_id"]
    if blocked_report["candidates"][0]["confidence"] != "exact":
        raise AssertionError("same-DOI candidate was not marked exact")
    if workspace_snapshot(import_workspace) != before_duplicate:
        raise AssertionError("blocked dry-run changed the workspace")
    if hashlib.sha256(duplicate_bib.read_bytes()).hexdigest() != duplicate_source_hash:
        raise AssertionError("blocked dry-run changed the source bibliography")

    reversed_duplicate_bib = args.root / "duplicate-doi-reversed.bib"
    reversed_duplicate_bib.write_text(
        "@article{DoiB, title={Second title}, author={E}, year={2024}, "
        "doi={doi:10.5555/duplicate.test}}\n"
        "@article{DoiA, title={=2+3 <b>First</b>}, author={D}, year={2025}, "
        "doi={https://doi.org/10.5555/Duplicate.Test}}\n",
        encoding="utf-8",
        newline="\n",
    )
    reversed_report = json.loads(
        run(
            [
                *cli,
                "import",
                "bibtex",
                str(reversed_duplicate_bib),
                "--workspace",
                str(import_workspace),
                "--dry-run",
            ],
            5,
        ).stdout
    )
    if reversed_report != blocked_report:
        raise AssertionError("dry-run report changed with bibliography record order")

    changed_duplicate_bib = args.root / "duplicate-doi-changed.bib"
    changed_duplicate_bib.write_text(
        "@article{DoiA, title={=2+3 <b>First</b>}, author={D}, year={2025}, "
        "doi={10.5555/Changed}}\n"
        "@article{DoiB, title={Second title}, author={E}, year={2024}, "
        "doi={doi:10.5555/changed}}\n",
        encoding="utf-8",
        newline="\n",
    )
    run(
        [
            *cli,
            "import",
            "bibtex",
            str(changed_duplicate_bib),
            "--workspace",
            str(import_workspace),
            "--accept-candidate",
            candidate_id,
        ],
        1,
    )
    if workspace_snapshot(import_workspace) != before_duplicate:
        raise AssertionError("stale candidate acceptance changed the workspace")
    run(
        [
            *cli,
            "import",
            "bibtex",
            str(duplicate_bib),
            "--workspace",
            str(import_workspace),
            "--accept-candidate",
            candidate_id,
        ]
    )
    duplicate_report = json.loads(
        run([str(entrypoint), "duplicates", "--workspace", str(import_workspace)]).stdout
    )
    if duplicate_report["candidate_group_count"] != 1:
        raise AssertionError("accepted duplicate candidate was not discoverable afterward")
    duplicate_csv = args.root / "duplicate-candidates.csv"
    duplicate_markdown = args.root / "duplicate-candidates.md"
    run(
        [
            *cli,
            "duplicates",
            "--workspace",
            str(import_workspace),
            "--format",
            "csv",
            "--output",
            str(duplicate_csv),
        ]
    )
    run(
        [
            *cli,
            "duplicates",
            "--workspace",
            str(import_workspace),
            "--format",
            "markdown",
            "--output",
            str(duplicate_markdown),
        ]
    )
    if not duplicate_csv.read_text(encoding="utf-8").startswith("candidate_id,confidence"):
        raise AssertionError("duplicate CSV did not contain the stable header")
    duplicate_csv_text = duplicate_csv.read_text(encoding="utf-8")
    if "'=2+3 <b>First</b>" not in duplicate_csv_text:
        raise AssertionError("duplicate CSV did not neutralize a spreadsheet formula")
    duplicate_markdown_text = duplicate_markdown.read_text(encoding="utf-8")
    if "Bibliography duplicate candidates" not in duplicate_markdown_text:
        raise AssertionError("duplicate Markdown report was not generated")
    if "&lt;b&gt;First&lt;/b&gt;" not in duplicate_markdown_text:
        raise AssertionError("duplicate Markdown did not escape raw HTML")

    workspace = args.root / "review"
    run([*cli, "demo", str(workspace)])
    run([*cli, "audit", "--workspace", str(workspace)])
    run([*cli, "agreement", "--workspace", str(workspace)])

    second = args.root / "review-second.json"
    write_json(
        second,
        {
            "id": "review-second",
            "paper_id": "edgeformer-2025",
            "kind": "individual",
            "reviewer": "Synthetic second reviewer",
            "ratings": ratings("no"),
        },
    )
    run([*cli, "add", "assessment", str(second), "--workspace", str(workspace)])

    conflict_agreement = workspace / "reports" / "conflict-agreement.json"
    conflict_audit = workspace / "reports" / "conflict-audit.json"
    run(
        [*cli, "agreement", "--workspace", str(workspace), "--output", str(conflict_agreement)],
        4,
    )
    run([*cli, "audit", "--workspace", str(workspace), "--output", str(conflict_audit)], 2)
    blocked_outputs = []
    for command in ("assess", "matrix", "triage"):
        output = workspace / "reports" / f"blocked-{command}.json"
        run([*cli, command, "--workspace", str(workspace), "--output", str(output)], 1)
        if output.exists():
            blocked_outputs.append(output.name)
    if blocked_outputs:
        raise AssertionError(f"conflicted commands wrote outputs: {', '.join(blocked_outputs)}")
    conflict = json.loads(conflict_agreement.read_text(encoding="utf-8"))
    edge_conflict = next(row for row in conflict["papers"] if row["paper_id"] == "edgeformer-2025")
    if edge_conflict["status"] != "conflict" or edge_conflict["selected_assessment_id"] is not None:
        raise AssertionError("unresolved reviews were not reported as a conflict")

    consensus = args.root / "consensus-one.json"
    source_ids = ["assess-edgeformer", "review-second"]
    source_hashes = {
        source_id: digest(
            json.loads(
                (workspace / "assessments" / f"{source_id}.json").read_text(encoding="utf-8")
            )
        )
        for source_id in source_ids
    }
    write_json(
        consensus,
        {
            "id": "consensus-one",
            "paper_id": "edgeformer-2025",
            "kind": "consensus",
            "reviewer": "Synthetic consensus after discussion",
            "source_assessment_ids": source_ids,
            "source_assessment_hashes": source_hashes,
            "ratings": ratings("partial"),
        },
    )
    run([*cli, "add", "assessment", str(consensus), "--workspace", str(workspace)])
    resolved = workspace / "reports" / "resolved-assess.json"
    run([*cli, "agreement", "--workspace", str(workspace)])
    run([*cli, "audit", "--workspace", str(workspace)])
    run([*cli, "assess", "--workspace", str(workspace), "--output", str(resolved)])
    run([*cli, "matrix", "--workspace", str(workspace)])
    run([*cli, "triage", "--workspace", str(workspace)])
    run([*cli, "report", "--workspace", str(workspace), "--output", "reports/resolved.html"])
    assessment = json.loads(resolved.read_text(encoding="utf-8"))
    edge_score = next(row for row in assessment["papers"] if row["paper_id"] == "edgeformer-2025")
    if edge_score["assessment_id"] != "consensus-one" or edge_score["score"] != 50.0:
        raise AssertionError("derived score did not use the explicit consensus")

    broken = args.root / "broken-review"
    run([*cli, "demo", str(broken)])
    (broken / "papers" / "broken.json").write_text("{\n", encoding="utf-8", newline="\n")
    broken_audit = broken / "reports" / "broken-audit.json"
    run([*cli, "audit", "--workspace", str(broken), "--output", str(broken_audit)], 2)
    malformed = json.loads(broken_audit.read_text(encoding="utf-8"))
    if "papers/broken.json" not in {item["artifact"] for item in malformed["issues"]}:
        raise AssertionError("malformed artifact path is missing from the audit")

    long_workspace = args.root / ("d" * 64) / "long-id-review"
    run(
        [
            *cli,
            "init",
            str(long_workspace),
            "--title",
            "Long path acceptance",
            "--question",
            "Can the portable ID limit survive a deep Windows workspace?",
        ]
    )
    long_id = "a" + "1" * 199
    long_task = args.root / "long-task.json"
    write_json(long_task, {"id": long_id, "title": "Maximum-length identifier"})
    stored = long_workspace / "tasks" / f"{long_id}.json"
    if len(str(stored)) <= 260:
        raise AssertionError(f"long-path acceptance target is too short: {len(str(stored))}")
    run([*cli, "add", "task", str(long_task), "--workspace", str(long_workspace)])
    run([*cli, "audit", "--workspace", str(long_workspace)])
    run(
        [
            *cli,
            "add",
            "task",
            str(long_task),
            "--workspace",
            str(long_workspace),
            "--replace",
        ]
    )

    print(
        json.dumps(
            {
                "status": "pass",
                "version": version,
                "conflict_exit": 4,
                "audit_conflict_exit": 2,
                "selected_assessment_id": edge_score["assessment_id"],
                "malformed_artifact": "papers/broken.json",
                "duplicate_candidate_id": candidate_id,
                "late_collision_side_effects": 0,
                "long_path_characters": len(str(stored)),
                "deep_workspace_characters": len(str(deep_workspace)),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

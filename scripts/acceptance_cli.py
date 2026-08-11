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


def run(command: list[str], expected: int = 0) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "PYTHONUTF8": "1"}
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
    if version != "reproweave 0.3.0":
        raise AssertionError(f"unexpected installed version: {version}")
    if run([str(entrypoint), "--version"]).stdout.strip() != version:
        raise AssertionError("console script version differs from python -m entry point")
    entrypoint_workspace = args.root / "entrypoint-review"
    run([str(entrypoint), "demo", str(entrypoint_workspace)])
    run([str(entrypoint), "audit", "--workspace", str(entrypoint_workspace)])

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

    print(
        json.dumps(
            {
                "status": "pass",
                "version": version,
                "conflict_exit": 4,
                "audit_conflict_exit": 2,
                "selected_assessment_id": edge_score["assessment_id"],
                "malformed_artifact": "papers/broken.json",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

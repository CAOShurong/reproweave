"""Cross-reference, provenance, and completeness checks."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .constants import ARTIFACT_KINDS
from .errors import CycleError, ReproWeaveError
from .graph import topological_tasks
from .workspace import Workspace


def _issue(level: str, code: str, message: str, artifact: str = "") -> dict[str, str]:
    return {"level": level, "code": code, "message": message, "artifact": artifact}


def audit_workspace(workspace: Workspace) -> dict[str, Any]:
    """Validate every artifact plus the relationships between them."""
    issues: list[dict[str, str]] = []
    records: dict[str, dict[str, dict[str, Any]]] = {}
    try:
        workspace.manifest()
    except ReproWeaveError as exc:
        issues.append(_issue("error", "manifest.invalid", str(exc), "reproweave.json"))
    for kind in ARTIFACT_KINDS:
        try:
            records[kind] = workspace.index(kind)
        except ReproWeaveError as exc:
            records[kind] = {}
            issues.append(_issue("error", f"{kind}.invalid", str(exc), kind))

    papers = records["paper"]
    experiments = records["experiment"]
    resources = records["resource"]
    tasks = records["task"]

    for claim in records["claim"].values():
        if claim["paper_id"] not in papers:
            issues.append(
                _issue(
                    "error",
                    "claim.paper_missing",
                    f"paper {claim['paper_id']} does not exist",
                    claim["id"],
                )
            )
        for experiment_id in claim.get("experiment_ids", []):
            if experiment_id not in experiments:
                issues.append(
                    _issue(
                        "error",
                        "claim.experiment_missing",
                        f"experiment {experiment_id} does not exist",
                        claim["id"],
                    )
                )
    for experiment in experiments.values():
        if experiment["paper_id"] not in papers:
            issues.append(
                _issue(
                    "error",
                    "experiment.paper_missing",
                    f"paper {experiment['paper_id']} does not exist",
                    experiment["id"],
                )
            )
        for resource_id in experiment.get("resource_ids", []):
            if resource_id not in resources:
                issues.append(
                    _issue(
                        "error",
                        "experiment.resource_missing",
                        f"resource {resource_id} does not exist",
                        experiment["id"],
                    )
                )
    for assessment in records["assessment"].values():
        if assessment["paper_id"] not in papers:
            issues.append(
                _issue(
                    "error",
                    "assessment.paper_missing",
                    f"paper {assessment['paper_id']} does not exist",
                    assessment["id"],
                )
            )
        if len(assessment.get("ratings", {})) < 8:
            issues.append(
                _issue(
                    "warning",
                    "assessment.incomplete",
                    "not every rubric dimension has an explicit rating",
                    assessment["id"],
                )
            )
    for item in records["screening"].values():
        if item["paper_id"] not in papers:
            issues.append(
                _issue(
                    "error",
                    "screening.paper_missing",
                    f"paper {item['paper_id']} does not exist",
                    item["id"],
                )
            )
    for task in tasks.values():
        for dependency in task.get("depends_on", []):
            if dependency not in tasks:
                issues.append(
                    _issue(
                        "error",
                        "task.dependency_missing",
                        f"task {dependency} does not exist",
                        task["id"],
                    )
                )
        for paper_id in task.get("paper_ids", []):
            if paper_id not in papers:
                issues.append(
                    _issue(
                        "error",
                        "task.paper_missing",
                        f"paper {paper_id} does not exist",
                        task["id"],
                    )
                )
    try:
        topological_tasks(list(tasks.values()))
    except CycleError as exc:
        issues.append(_issue("error", "task.cycle", str(exc), "tasks"))

    assessed = {item["paper_id"] for item in records["assessment"].values()}
    included = {
        item["paper_id"]
        for item in records["screening"].values()
        if item.get("state") == "included"
    }
    for paper_id in sorted(included - assessed):
        issues.append(
            _issue(
                "warning",
                "paper.unassessed",
                "included paper has no reconstructability assessment",
                paper_id,
            )
        )

    counts = Counter(item["level"] for item in issues)
    issues.sort(key=lambda item: ({"error": 0, "warning": 1}.get(item["level"], 2), item["code"]))
    return {
        "status": "pass" if not counts["error"] else "fail",
        "root": str(Path(workspace.root)),
        "counts": {
            "errors": counts["error"],
            "warnings": counts["warning"],
            "artifacts": sum(len(items) for items in records.values()),
            **workspace.counts(),
        },
        "issues": issues,
        "checks": [
            "artifact schemas",
            "cross references",
            "task dependency cycles",
            "included-paper assessment coverage",
        ],
    }

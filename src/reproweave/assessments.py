"""Explicit resolution of individual and consensus assessments."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from .constants import ASSESSMENT_DIMENSIONS
from .errors import ValidationError
from .util import canonical_json, sha256_text
from .workspace import Workspace


def _issue(code: str, message: str, artifact: str) -> dict[str, str]:
    return {"level": "error", "code": code, "message": message, "artifact": artifact}


def assessment_digest(value: dict[str, Any]) -> str:
    """Bind a consensus decision to the exact canonical bytes of one source card."""
    return sha256_text(canonical_json(value))


def analyze_assessments(
    assessments: Iterable[dict[str, Any]],
    paper_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Describe how assessment cards resolve without guessing across reviewers."""
    items = sorted(assessments, key=lambda item: item["id"])
    by_id = {item["id"]: item for item in items}
    by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_paper[item["paper_id"]].append(item)

    issues: list[dict[str, str]] = []
    rows: list[dict[str, Any]] = []
    all_paper_ids = sorted(set(paper_ids) | set(by_paper))
    for paper_id in all_paper_ids:
        paper_items = by_paper.get(paper_id, [])
        individuals = [
            item for item in paper_items if item.get("kind", "individual") == "individual"
        ]
        consensuses = [
            item for item in paper_items if item.get("kind", "individual") == "consensus"
        ]
        conflicting_dimensions = []
        if len(individuals) > 1:
            for dimension in ASSESSMENT_DIMENSIONS:
                values = {
                    item.get("ratings", {}).get(dimension, {}).get("rating", "missing")
                    for item in individuals
                }
                if len(values) > 1:
                    conflicting_dimensions.append(dimension)

        status = "missing"
        selected: dict[str, Any] | None = None
        if len(consensuses) > 1:
            status = "invalid"
            issues.append(
                _issue(
                    "assessment.consensus_multiple",
                    f"paper {paper_id} has multiple consensus assessments: "
                    + ", ".join(item["id"] for item in consensuses),
                    paper_id,
                )
            )
        elif consensuses:
            consensus = consensuses[0]
            source_ids = consensus.get("source_assessment_ids", [])
            source_hashes = consensus.get("source_assessment_hashes", {})
            semantic_errors = False
            for source_id in source_ids:
                source = by_id.get(source_id)
                if source is None:
                    semantic_errors = True
                    issues.append(
                        _issue(
                            "assessment.consensus_source_missing",
                            f"consensus {consensus['id']} references missing assessment {source_id}",
                            consensus["id"],
                        )
                    )
                elif source.get("kind", "individual") != "individual":
                    semantic_errors = True
                    issues.append(
                        _issue(
                            "assessment.consensus_source_not_individual",
                            f"consensus {consensus['id']} source {source_id} is not individual",
                            consensus["id"],
                        )
                    )
                elif source["paper_id"] != paper_id:
                    semantic_errors = True
                    issues.append(
                        _issue(
                            "assessment.consensus_source_paper_mismatch",
                            f"consensus {consensus['id']} source {source_id} evaluates "
                            f"paper {source['paper_id']}, not {paper_id}",
                            consensus["id"],
                        )
                    )
                elif source_hashes.get(source_id) != assessment_digest(source):
                    semantic_errors = True
                    issues.append(
                        _issue(
                            "assessment.consensus_source_changed",
                            f"consensus {consensus['id']} does not bind the current content of "
                            f"source {source_id}; record a new consensus",
                            consensus["id"],
                        )
                    )
            expected_sources = {item["id"] for item in individuals}
            if set(source_ids) != expected_sources:
                semantic_errors = True
                missing_sources = sorted(expected_sources - set(source_ids))
                extra_sources = sorted(set(source_ids) - expected_sources)
                detail = []
                if missing_sources:
                    detail.append("missing " + ", ".join(missing_sources))
                if extra_sources:
                    detail.append("unexpected " + ", ".join(extra_sources))
                issues.append(
                    _issue(
                        "assessment.consensus_incomplete",
                        f"consensus {consensus['id']} must cover every individual assessment"
                        + (f" ({'; '.join(detail)})" if detail else ""),
                        consensus["id"],
                    )
                )
            if semantic_errors:
                status = "invalid"
            else:
                status = "resolved"
                selected = consensus
        elif len(individuals) == 1:
            status = "resolved"
            selected = individuals[0]
        elif len(individuals) > 1:
            status = "conflict"
            issues.append(
                _issue(
                    "assessment.conflict",
                    f"paper {paper_id} has {len(individuals)} individual assessments; "
                    "add one explicit consensus assessment covering all of them",
                    paper_id,
                )
            )

        rows.append(
            {
                "paper_id": paper_id,
                "status": status,
                "resolution": (
                    "consensus"
                    if selected is not None and selected.get("kind", "individual") == "consensus"
                    else "single"
                    if selected is not None
                    else None
                ),
                "individual_assessment_ids": [item["id"] for item in individuals],
                "individual_assessment_hashes": {
                    item["id"]: assessment_digest(item) for item in individuals
                },
                "consensus_assessment_id": consensuses[0]["id"] if len(consensuses) == 1 else None,
                "selected_assessment_id": selected["id"] if selected else None,
                "conflicting_dimensions": conflicting_dimensions,
            }
        )

    counts = defaultdict(int)
    for row in rows:
        counts[row["status"]] += 1
    return {
        "papers": rows,
        "summary": {
            "paper_count": len(all_paper_ids),
            "assessment_count": len(items),
            "resolved_paper_count": counts["resolved"],
            "conflicted_paper_count": counts["conflict"],
            "invalid_paper_count": counts["invalid"],
            "missing_paper_count": counts["missing"],
        },
        "issues": sorted(
            issues, key=lambda item: (item["code"], item["artifact"], item["message"])
        ),
        "interpretation": (
            "Individual reviews remain separate. Multiple reviews require an explicit consensus; "
            "ReproWeave never averages ratings or chooses a majority automatically."
        ),
    }


def build_assessment_resolution(workspace: Workspace) -> dict[str, Any]:
    """Build a workspace-level reviewer and consensus status report."""
    return analyze_assessments(
        workspace.all("assessment"),
        (paper["id"] for paper in workspace.all("paper")),
    )


def resolved_assessment_index(workspace: Workspace) -> dict[str, dict[str, Any]]:
    """Return one explicit assessment per paper or fail on unresolved ambiguity."""
    assessments = workspace.all("assessment")
    by_id = {item["id"]: item for item in assessments}
    result = analyze_assessments(
        assessments,
        (paper["id"] for paper in workspace.all("paper")),
    )
    if result["issues"]:
        first = result["issues"][0]
        raise ValidationError(
            f"assessment resolution failed: {first['message']}; run `reproweave agreement` "
            "and record an explicit consensus"
        )
    return {
        row["paper_id"]: by_id[row["selected_assessment_id"]]
        for row in result["papers"]
        if row["selected_assessment_id"] is not None
    }

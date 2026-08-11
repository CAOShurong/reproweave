"""Rule-based replication-candidate triage with explicit decision boundaries."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .assessments import resolved_assessment_index
from .constants import ASSESSMENT_DIMENSIONS
from .errors import ValidationError
from .scoring import score_assessment
from .workspace import Workspace

AVAILABILITY_VALUES = {"available", "partial", "unavailable", "unknown"}
STATUS_RANK = {
    "complete": 0,
    "run_now": 1,
    "prepare": 2,
    "evidence_first": 3,
    "needs_planning": 4,
}


def parse_resource_overrides(values: list[str] | None) -> dict[str, str]:
    """Parse repeatable ``RESOURCE=AVAILABILITY`` CLI values."""
    overrides: dict[str, str] = {}
    for raw in values or []:
        resource_id, separator, availability = raw.partition("=")
        resource_id = resource_id.strip()
        availability = availability.strip()
        if not separator or not resource_id or availability not in AVAILABILITY_VALUES:
            choices = ", ".join(sorted(AVAILABILITY_VALUES))
            raise ValidationError(
                f"resource override must be RESOURCE=AVAILABILITY, where AVAILABILITY is {choices}"
            )
        overrides[resource_id] = availability
    return overrides


def _assessment_gaps(assessment: dict[str, Any] | None) -> list[dict[str, str]]:
    if not assessment:
        return []
    gaps = []
    for dimension in ASSESSMENT_DIMENSIONS:
        detail = assessment.get("ratings", {}).get(dimension)
        rating = detail.get("rating", "missing") if detail else "missing"
        if rating in {"partial", "no", "unknown", "missing"}:
            gaps.append(
                {
                    "dimension": dimension,
                    "rating": rating,
                    "next_action": (
                        detail.get("next_action", f"Resolve {dimension} evidence.")
                        if detail
                        else f"Assess {dimension} evidence."
                    ),
                }
            )
    return gaps


def _decision(
    *,
    assessment: dict[str, Any] | None,
    tasks: list[dict[str, Any]],
    hard_blocked_tasks: list[dict[str, Any]],
    resources: list[dict[str, Any]],
) -> tuple[str, str]:
    unresolved_resources = [
        item for item in resources if item["effective_availability"] != "available"
    ]
    hard_evidence_gaps = [
        item
        for item in _assessment_gaps(assessment)
        if item["rating"] in {"no", "unknown", "missing"}
    ]
    remaining_tasks = [item for item in tasks if item.get("state", "ready") != "done"]
    if not assessment or not tasks:
        return "needs_planning", "Add an assessment card and a paper-linked task plan."
    if not remaining_tasks and not unresolved_resources and not hard_evidence_gaps:
        return "complete", "Archive the reproduced outputs and record claim-level outcomes."
    if unresolved_resources:
        first = unresolved_resources[0]
        return (
            "evidence_first",
            f"Resolve {first['name']} ({first['effective_availability']}).",
        )
    if hard_blocked_tasks:
        return "evidence_first", f"Unblock task: {hard_blocked_tasks[0]['title']}."
    if hard_evidence_gaps:
        first = hard_evidence_gaps[0]
        return "evidence_first", first["next_action"]
    if remaining_tasks and any(item.get("state", "ready") == "ready" for item in remaining_tasks):
        first = next(item for item in remaining_tasks if item.get("state", "ready") == "ready")
        return "run_now", f"Start task: {first['title']}."
    return "prepare", "Resolve partial evidence and confirm the next runnable task."


def build_replication_triage(
    workspace: Workspace,
    resource_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Combine evidence, resources, and work into a transparent candidate queue."""
    overrides = dict(resource_overrides or {})
    resource_index = workspace.index("resource")
    unknown_overrides = sorted(set(overrides) - set(resource_index))
    if unknown_overrides:
        raise ValidationError(
            f"resource override references unknown IDs: {', '.join(unknown_overrides)}"
        )
    invalid_values = sorted(set(overrides.values()) - AVAILABILITY_VALUES)
    if invalid_values:
        raise ValidationError(
            f"resource override has invalid availability values: {', '.join(invalid_values)}"
        )

    assessments = resolved_assessment_index(workspace)
    experiments_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for experiment in workspace.all("experiment"):
        experiments_by_paper[experiment["paper_id"]].append(experiment)
    tasks = workspace.all("task")
    tasks_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    task_index = {item["id"]: item for item in tasks}
    for task in tasks:
        for paper_id in task.get("paper_ids", []):
            tasks_by_paper[paper_id].append(task)

    rows = []
    for paper in workspace.all("paper"):
        paper_id = paper["id"]
        assessment = assessments.get(paper_id)
        assessment_result = score_assessment(assessment) if assessment else None
        paper_tasks = sorted(tasks_by_paper[paper_id], key=lambda item: item["id"])
        hard_blocked_tasks = [
            item
            for item in paper_tasks
            if item.get("state", "ready") == "blocked"
            or any(
                task_index.get(dependency, {}).get("state", "ready") != "done"
                for dependency in item.get("depends_on", [])
            )
        ]
        resource_ids = sorted(
            {
                resource_id
                for experiment in experiments_by_paper[paper_id]
                for resource_id in experiment.get("resource_ids", [])
            }
        )
        resource_rows = []
        for resource_id in resource_ids:
            resource = resource_index.get(resource_id, {})
            recorded = resource.get("availability", "unknown")
            effective = overrides.get(resource_id, recorded)
            resource_rows.append(
                {
                    "id": resource_id,
                    "name": resource.get("name", resource_id),
                    "kind": resource.get("kind", "unknown"),
                    "recorded_availability": recorded,
                    "effective_availability": effective,
                    "overridden": resource_id in overrides,
                }
            )
        status, next_action = _decision(
            assessment=assessment,
            tasks=paper_tasks,
            hard_blocked_tasks=hard_blocked_tasks,
            resources=resource_rows,
        )
        remaining_tasks = [item for item in paper_tasks if item.get("state", "ready") != "done"]
        gaps = _assessment_gaps(assessment)
        rows.append(
            {
                "paper_id": paper_id,
                "title": paper["title"],
                "year": paper["year"],
                "status": status,
                "next_action": next_action,
                "reconstructability_score": (
                    assessment_result["score"] if assessment_result else None
                ),
                "rubric_coverage": (
                    assessment_result["rubric_coverage"] if assessment_result else 0.0
                ),
                "evidence_gaps": gaps,
                "required_resources": resource_rows,
                "unresolved_resource_ids": [
                    item["id"]
                    for item in resource_rows
                    if item["effective_availability"] != "available"
                ],
                "task_count": len(paper_tasks),
                "remaining_task_count": len(remaining_tasks),
                "remaining_effort_hours": round(
                    sum(item.get("estimate_hours", 0) for item in remaining_tasks), 1
                ),
                "blocked_task_ids": [item["id"] for item in hard_blocked_tasks],
            }
        )
    rows.sort(
        key=lambda item: (
            STATUS_RANK[item["status"]],
            len(item["unresolved_resource_ids"]),
            len(item["blocked_task_ids"]),
            item["remaining_effort_hours"],
            -(item["reconstructability_score"] or 0),
            item["paper_id"],
        )
    )
    status_counts = Counter(item["status"] for item in rows)
    return {
        "candidates": rows,
        "summary": {
            "paper_count": len(rows),
            "status_counts": {status: status_counts.get(status, 0) for status in STATUS_RANK},
            "run_now_ids": [item["paper_id"] for item in rows if item["status"] == "run_now"],
            "evidence_first_ids": [
                item["paper_id"] for item in rows if item["status"] == "evidence_first"
            ],
        },
        "scenario": {
            "resource_overrides": dict(sorted(overrides.items())),
            "override_count": len(overrides),
        },
        "decision_rules": {
            "complete": "All linked tasks are done and no hard evidence or resource gap remains.",
            "run_now": "A linked task is ready and no hard evidence, resource, or dependency blocker remains.",
            "prepare": "No hard blocker remains, but partial evidence or task state still needs preparation.",
            "evidence_first": "A resource, task dependency, or no/unknown/missing evidence item blocks execution.",
            "needs_planning": "The paper lacks either an assessment card or a linked task plan.",
        },
        "interpretation": (
            "This is a rule-based execution queue, not a scientific-quality or novelty ranking. "
            "Scores and hour estimates remain human-entered evidence and planning inputs."
        ),
    }

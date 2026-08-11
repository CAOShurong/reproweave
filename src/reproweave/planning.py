"""Replication plan scheduling and resource summaries."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .assessments import resolved_assessment_index
from .graph import topological_tasks
from .workspace import Workspace

PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def build_replication_plan(workspace: Workspace) -> dict[str, Any]:
    """Turn task dependencies into executable waves and blocker summaries."""
    tasks = workspace.all("task")
    ordered = topological_tasks(tasks)
    by_id = {task["id"]: task for task in tasks}
    wave_by_id: dict[str, int] = {}
    waves: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for task in ordered:
        dependencies = [item for item in task.get("depends_on", []) if item in by_id]
        wave = max((wave_by_id[item] + 1 for item in dependencies), default=0)
        wave_by_id[task["id"]] = wave
        enriched = dict(task)
        enriched["wave"] = wave
        enriched["blocked_by"] = [
            dependency
            for dependency in dependencies
            if by_id[dependency].get("state", "ready") != "done"
        ]
        waves[wave].append(enriched)
    rendered_waves = []
    for wave, wave_tasks in sorted(waves.items()):
        wave_tasks.sort(
            key=lambda item: (PRIORITY_RANK[item.get("priority", "medium")], item["id"])
        )
        rendered_waves.append(
            {
                "wave": wave,
                "parallel_tasks": wave_tasks,
                "effort_hours": round(sum(item.get("estimate_hours", 0) for item in wave_tasks), 1),
                "critical_path_hours": max(
                    (item.get("estimate_hours", 0) for item in wave_tasks), default=0
                ),
            }
        )
    blockers = [
        {
            "task_id": task["id"],
            "title": task["title"],
            "blocked_by": task["blocked_by"],
            "notes": task.get("blocker", ""),
        }
        for group in rendered_waves
        for task in group["parallel_tasks"]
        if task.get("state") == "blocked" or task["blocked_by"]
    ]
    state_counts = Counter(task.get("state", "ready") for task in tasks)
    return {
        "waves": rendered_waves,
        "summary": {
            "task_count": len(tasks),
            "total_effort_hours": round(sum(task.get("estimate_hours", 0) for task in tasks), 1),
            "ideal_parallel_hours": round(
                sum(group["critical_path_hours"] for group in rendered_waves), 1
            ),
            "blocked_count": len(blockers),
            "state_counts": dict(sorted(state_counts.items())),
        },
        "blockers": blockers,
        "assumption": (
            "Ideal parallel hours assumes unlimited people and hardware within each wave; "
            "estimates are planning inputs, not observed duration."
        ),
    }


def readiness_backlog(workspace: Workspace) -> list[dict[str, Any]]:
    """Rank unresolved assessment gaps into an evidence-gathering backlog."""
    tasks = []
    for assessment in resolved_assessment_index(workspace).values():
        for dimension, detail in assessment.get("ratings", {}).items():
            if detail["rating"] in {"no", "unknown", "partial"}:
                severity = {"no": "high", "unknown": "high", "partial": "medium"}[detail["rating"]]
                tasks.append(
                    {
                        "paper_id": assessment["paper_id"],
                        "dimension": dimension,
                        "severity": severity,
                        "current_rating": detail["rating"],
                        "evidence": detail["evidence"],
                        "next_action": detail.get(
                            "next_action", f"Resolve missing {dimension} evidence."
                        ),
                    }
                )
    return sorted(
        tasks,
        key=lambda item: (
            PRIORITY_RANK[item["severity"]],
            item["paper_id"],
            item["dimension"],
        ),
    )

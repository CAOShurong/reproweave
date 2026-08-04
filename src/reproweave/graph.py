"""Evidence graph construction and traversal."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from .errors import CycleError
from .workspace import Workspace


def build_evidence_graph(workspace: Workspace) -> dict[str, Any]:
    """Build a typed graph from explicit workspace references."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    for paper in workspace.all("paper"):
        nodes.append({"id": paper["id"], "kind": "paper", "label": paper["title"]})
    for claim in workspace.all("claim"):
        nodes.append({"id": claim["id"], "kind": "claim", "label": claim["statement"]})
        edges.append({"source": claim["paper_id"], "target": claim["id"], "type": "reports"})
        for experiment_id in claim.get("experiment_ids", []):
            edges.append({"source": claim["id"], "target": experiment_id, "type": "supported-by"})
    for experiment in workspace.all("experiment"):
        nodes.append({"id": experiment["id"], "kind": "experiment", "label": experiment["name"]})
        edges.append(
            {"source": experiment["paper_id"], "target": experiment["id"], "type": "contains"}
        )
        for resource_id in experiment.get("resource_ids", []):
            edges.append({"source": experiment["id"], "target": resource_id, "type": "uses"})
    for resource in workspace.all("resource"):
        nodes.append({"id": resource["id"], "kind": "resource", "label": resource["name"]})
    for task in workspace.all("task"):
        nodes.append({"id": task["id"], "kind": "task", "label": task["title"]})
        for paper_id in task.get("paper_ids", []):
            edges.append({"source": task["id"], "target": paper_id, "type": "replicates"})
        for dependency in task.get("depends_on", []):
            edges.append({"source": dependency, "target": task["id"], "type": "unblocks"})
    return {
        "nodes": sorted(nodes, key=lambda item: (item["kind"], item["id"])),
        "edges": sorted(edges, key=lambda item: (item["source"], item["target"], item["type"])),
    }


def topological_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order tasks by dependencies with deterministic tie-breaking."""
    by_id = {task["id"]: task for task in tasks}
    incoming = {task_id: 0 for task_id in by_id}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        for dependency in task.get("depends_on", []):
            if dependency in by_id:
                incoming[task["id"]] += 1
                outgoing[dependency].append(task["id"])
    queue = deque(sorted(task_id for task_id, count in incoming.items() if count == 0))
    result: list[dict[str, Any]] = []
    while queue:
        task_id = queue.popleft()
        result.append(by_id[task_id])
        for target in sorted(outgoing[task_id]):
            incoming[target] -= 1
            if incoming[target] == 0:
                queue.append(target)
        queue = deque(sorted(queue))
    if len(result) != len(tasks):
        cycle_nodes = sorted(task_id for task_id, count in incoming.items() if count > 0)
        raise CycleError(f"replication task cycle: {', '.join(cycle_nodes)}")
    return result

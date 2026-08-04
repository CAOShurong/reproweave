"""Transparent reconstructability scoring."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .constants import ASSESSMENT_DIMENSIONS, RATING_VALUES
from .workspace import Workspace


def score_assessment(assessment: dict[str, Any]) -> dict[str, Any]:
    """Compute coverage without converting unknown evidence into false precision."""
    numerator = 0.0
    denominator = 0.0
    answered = 0
    gaps: list[str] = []
    for dimension, metadata in ASSESSMENT_DIMENSIONS.items():
        detail = assessment.get("ratings", {}).get(dimension)
        if not detail:
            gaps.append(dimension)
            continue
        rating = detail["rating"]
        value = RATING_VALUES[rating]
        if value is None:
            continue
        weight = float(metadata["weight"])
        numerator += value * weight
        denominator += weight
        answered += 1
        if rating in {"no", "unknown"}:
            gaps.append(dimension)
    score = round((100 * numerator / denominator), 1) if denominator else 0.0
    coverage = round((100 * answered / len(ASSESSMENT_DIMENSIONS)), 1)
    return {
        "assessment_id": assessment["id"],
        "paper_id": assessment["paper_id"],
        "score": score,
        "rubric_coverage": coverage,
        "answered_dimensions": answered,
        "applicable_weight": round(denominator, 2),
        "gaps": gaps,
        "interpretation": "reconstructability coverage, not scientific quality",
    }


def assess_workspace(workspace: Workspace) -> dict[str, Any]:
    """Summarize paper assessments and the most common evidence gaps."""
    papers = workspace.index("paper")
    rows = []
    gap_counts: Counter[str] = Counter()
    assessed: set[str] = set()
    for assessment in workspace.all("assessment"):
        result = score_assessment(assessment)
        result["title"] = papers.get(result["paper_id"], {}).get("title", result["paper_id"])
        rows.append(result)
        assessed.add(result["paper_id"])
        gap_counts.update(result["gaps"])
    rows.sort(key=lambda item: (-item["score"], item["paper_id"]))
    scores = [item["score"] for item in rows]
    return {
        "papers": rows,
        "summary": {
            "paper_count": len(papers),
            "assessed_count": len(rows),
            "unassessed_paper_ids": sorted(set(papers) - assessed),
            "mean_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
            "minimum_score": min(scores, default=0.0),
            "maximum_score": max(scores, default=0.0),
            "common_gaps": [
                {"dimension": key, "count": count} for key, count in gap_counts.most_common()
            ],
        },
        "rubric": ASSESSMENT_DIMENSIONS,
        "warning": (
            "Scores measure documented reconstructability. They do not judge correctness, "
            "importance, novelty, statistical validity, or research integrity."
        ),
    }


def evidence_matrix(workspace: Workspace) -> dict[str, Any]:
    """Return a rectangular paper-by-dimension matrix."""
    assessments = {item["paper_id"]: item for item in workspace.all("assessment")}
    rows = []
    for paper in workspace.all("paper"):
        assessment = assessments.get(paper["id"], {})
        ratings = assessment.get("ratings", {})
        row = {
            "paper_id": paper["id"],
            "title": paper["title"],
            "year": paper["year"],
        }
        for dimension in ASSESSMENT_DIMENSIONS:
            row[dimension] = ratings.get(dimension, {}).get("rating", "missing")
        rows.append(row)
    return {"dimensions": list(ASSESSMENT_DIMENSIONS), "rows": rows}

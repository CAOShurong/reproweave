"""Shared synthetic fixtures for tests."""

from __future__ import annotations

from pathlib import Path

from reproweave.workspace import Workspace


def make_workspace(root: Path) -> Workspace:
    workspace = Workspace.create(root, title="Test review", research_question="Can it rebuild?")
    workspace.add(
        "paper",
        {
            "id": "paper-one",
            "title": "Paper One",
            "authors": ["A. Author"],
            "year": 2025,
            "venue": "Test",
            "tags": [],
        },
    )
    return workspace


def full_ratings(rating: str = "yes") -> dict[str, dict[str, str]]:
    return {
        dimension: {"rating": rating, "evidence": f"Evidence for {dimension}."}
        for dimension in (
            "method",
            "data",
            "code",
            "environment",
            "metrics",
            "baselines",
            "compute",
            "results",
        )
    }

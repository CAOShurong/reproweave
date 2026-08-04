"""Stable vocabulary and defaults."""

from __future__ import annotations

FORMAT_VERSION = "1"
APP_VERSION = "0.2.0"

ARTIFACT_KINDS = (
    "paper",
    "claim",
    "experiment",
    "resource",
    "assessment",
    "task",
    "screening",
)

ASSESSMENT_DIMENSIONS = {
    "method": {
        "label": "Method specificity",
        "question": "Can an independent reader reconstruct the method from cited evidence?",
        "weight": 1.25,
    },
    "data": {
        "label": "Data availability",
        "question": "Are the exact inputs available or independently reconstructable?",
        "weight": 1.25,
    },
    "code": {
        "label": "Code availability",
        "question": "Is runnable code linked, versioned, and sufficiently licensed?",
        "weight": 1.0,
    },
    "environment": {
        "label": "Environment capture",
        "question": "Are software, dependencies, hardware, and random seeds recorded?",
        "weight": 1.0,
    },
    "metrics": {
        "label": "Metric definition",
        "question": "Are metrics, aggregation, and uncertainty fully specified?",
        "weight": 1.0,
    },
    "baselines": {
        "label": "Baseline traceability",
        "question": "Can the comparison baselines and their settings be identified?",
        "weight": 0.75,
    },
    "compute": {
        "label": "Compute disclosure",
        "question": "Are training or experimental compute requirements bounded?",
        "weight": 0.75,
    },
    "results": {
        "label": "Result traceability",
        "question": "Can each headline result be linked to a configuration and artifact?",
        "weight": 1.25,
    },
}

RATING_VALUES = {
    "yes": 1.0,
    "partial": 0.5,
    "no": 0.0,
    "unknown": 0.0,
    "na": None,
}

SCREENING_STATES = ("discovered", "deduplicated", "screened", "included", "excluded")
TASK_STATES = ("blocked", "ready", "in_progress", "done")
TASK_PRIORITIES = ("critical", "high", "medium", "low")
RESOURCE_KINDS = (
    "code",
    "dataset",
    "environment",
    "model",
    "hardware",
    "protocol",
    "result",
    "other",
)

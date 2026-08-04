"""Artifact validation kept deliberately explicit and dependency-free."""

from __future__ import annotations

from typing import Any

from .constants import (
    ASSESSMENT_DIMENSIONS,
    RATING_VALUES,
    RESOURCE_KINDS,
    SCREENING_STATES,
    TASK_PRIORITIES,
    TASK_STATES,
)
from .errors import ValidationError
from .util import ensure_id, ensure_text


def _list_of_ids(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be a list")
    return [ensure_id(item, field) for item in value]


def validate_paper(value: dict[str, Any]) -> dict[str, Any]:
    """Validate a bibliographic record without pretending to be a full citation manager."""
    ensure_id(value.get("id"), "paper.id")
    ensure_text(value.get("title"), "paper.title")
    authors = value.get("authors")
    if not isinstance(authors, list) or not authors:
        raise ValidationError("paper.authors must be a non-empty list")
    for author in authors:
        ensure_text(author, "paper.authors[]")
    year = value.get("year")
    if not isinstance(year, int) or not 1000 <= year <= 3000:
        raise ValidationError("paper.year must be an integer between 1000 and 3000")
    for field in ("doi", "url", "venue", "abstract", "notes"):
        if field in value and not isinstance(value[field], str):
            raise ValidationError(f"paper.{field} must be a string")
    tags = value.get("tags", [])
    if not isinstance(tags, list) or any(not isinstance(item, str) for item in tags):
        raise ValidationError("paper.tags must be a list of strings")
    return value


def validate_claim(value: dict[str, Any]) -> dict[str, Any]:
    ensure_id(value.get("id"), "claim.id")
    ensure_id(value.get("paper_id"), "claim.paper_id")
    ensure_text(value.get("statement"), "claim.statement")
    ensure_text(value.get("evidence_locator"), "claim.evidence_locator")
    claim_type = value.get("type", "empirical")
    if claim_type not in {"empirical", "method", "theory", "survey", "limitation"}:
        raise ValidationError("claim.type is not recognized")
    confidence = value.get("confidence", "reported")
    if confidence not in {"reported", "corroborated", "contested", "uncertain"}:
        raise ValidationError("claim.confidence is not recognized")
    _list_of_ids(value.get("experiment_ids"), "claim.experiment_ids")
    return value


def validate_experiment(value: dict[str, Any]) -> dict[str, Any]:
    ensure_id(value.get("id"), "experiment.id")
    ensure_id(value.get("paper_id"), "experiment.paper_id")
    ensure_text(value.get("name"), "experiment.name")
    ensure_text(value.get("protocol_summary"), "experiment.protocol_summary")
    for field in ("resource_ids", "metric_ids", "baseline_ids"):
        _list_of_ids(value.get(field), f"experiment.{field}")
    return value


def validate_resource(value: dict[str, Any]) -> dict[str, Any]:
    ensure_id(value.get("id"), "resource.id")
    ensure_text(value.get("name"), "resource.name")
    if value.get("kind") not in RESOURCE_KINDS:
        raise ValidationError(f"resource.kind must be one of {', '.join(RESOURCE_KINDS)}")
    availability = value.get("availability", "unknown")
    if availability not in {"available", "partial", "unavailable", "unknown"}:
        raise ValidationError("resource.availability is not recognized")
    for field in ("url", "version", "license", "checksum", "notes"):
        if field in value and not isinstance(value[field], str):
            raise ValidationError(f"resource.{field} must be a string")
    return value


def validate_assessment(value: dict[str, Any]) -> dict[str, Any]:
    ensure_id(value.get("id"), "assessment.id")
    ensure_id(value.get("paper_id"), "assessment.paper_id")
    ratings = value.get("ratings")
    if not isinstance(ratings, dict):
        raise ValidationError("assessment.ratings must be an object")
    unknown = set(ratings) - set(ASSESSMENT_DIMENSIONS)
    if unknown:
        raise ValidationError(f"unknown assessment dimensions: {', '.join(sorted(unknown))}")
    for dimension, detail in ratings.items():
        if not isinstance(detail, dict):
            raise ValidationError(f"assessment.ratings.{dimension} must be an object")
        if detail.get("rating") not in RATING_VALUES:
            raise ValidationError(f"invalid rating for {dimension}")
        ensure_text(detail.get("evidence"), f"assessment.ratings.{dimension}.evidence")
    return value


def validate_task(value: dict[str, Any]) -> dict[str, Any]:
    ensure_id(value.get("id"), "task.id")
    ensure_text(value.get("title"), "task.title")
    if value.get("state", "ready") not in TASK_STATES:
        raise ValidationError("task.state is not recognized")
    if value.get("priority", "medium") not in TASK_PRIORITIES:
        raise ValidationError("task.priority is not recognized")
    _list_of_ids(value.get("depends_on"), "task.depends_on")
    _list_of_ids(value.get("paper_ids"), "task.paper_ids")
    estimate = value.get("estimate_hours", 0)
    if not isinstance(estimate, (int, float)) or estimate < 0:
        raise ValidationError("task.estimate_hours must be non-negative")
    return value


def validate_screening(value: dict[str, Any]) -> dict[str, Any]:
    ensure_id(value.get("id"), "screening.id")
    ensure_id(value.get("paper_id"), "screening.paper_id")
    if value.get("state") not in SCREENING_STATES:
        raise ValidationError("screening.state is not recognized")
    ensure_text(value.get("reason"), "screening.reason")
    ensure_text(value.get("recorded_at"), "screening.recorded_at")
    return value


VALIDATORS = {
    "paper": validate_paper,
    "claim": validate_claim,
    "experiment": validate_experiment,
    "resource": validate_resource,
    "assessment": validate_assessment,
    "task": validate_task,
    "screening": validate_screening,
}


def validate(kind: str, value: dict[str, Any]) -> dict[str, Any]:
    """Validate one artifact by kind."""
    try:
        validator = VALIDATORS[kind]
    except KeyError as exc:
        raise ValidationError(f"unknown artifact kind: {kind}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"{kind} must be an object")
    return validator(value)

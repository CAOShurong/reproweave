"""Artifact validation kept deliberately explicit and dependency-free."""

from __future__ import annotations

import math
import re
from collections.abc import Collection
from typing import Any

from .constants import (
    ASSESSMENT_DIMENSIONS,
    MAX_ESTIMATE_HOURS,
    RATING_VALUES,
    RESOURCE_KINDS,
    SCREENING_STATES,
    TASK_PRIORITIES,
    TASK_STATES,
)
from .errors import ValidationError
from .util import ensure_id, ensure_text

SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _list_of_ids(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValidationError(f"{field} must be a list")
    return [ensure_id(item, field) for item in value]


def _choice(value: Any, choices: Collection[str], field: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise ValidationError(f"{field} is not recognized")
    return value


def _optional_strings(value: dict[str, Any], prefix: str, fields: tuple[str, ...]) -> None:
    for field in fields:
        if field in value and not isinstance(value[field], str):
            raise ValidationError(f"{prefix}.{field} must be a string")


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
    if (
        isinstance(year, bool)
        or not isinstance(year, (int, float))
        or (isinstance(year, float) and (not math.isfinite(year) or not year.is_integer()))
        or not 1000 <= year <= 3000
    ):
        raise ValidationError("paper.year must be an integer between 1000 and 3000")
    value["year"] = int(year)
    _optional_strings(value, "paper", ("doi", "url", "venue", "abstract", "notes", "source_key"))
    tags = value.get("tags", [])
    if not isinstance(tags, list) or any(not isinstance(item, str) for item in tags):
        raise ValidationError("paper.tags must be a list of strings")
    return value


def validate_claim(value: dict[str, Any]) -> dict[str, Any]:
    ensure_id(value.get("id"), "claim.id")
    ensure_id(value.get("paper_id"), "claim.paper_id")
    ensure_text(value.get("statement"), "claim.statement")
    ensure_text(value.get("evidence_locator"), "claim.evidence_locator")
    _choice(
        value.get("type", "empirical"),
        {"empirical", "method", "theory", "survey", "limitation"},
        "claim.type",
    )
    _choice(
        value.get("confidence", "reported"),
        {"reported", "corroborated", "contested", "uncertain"},
        "claim.confidence",
    )
    if "experiment_ids" in value:
        _list_of_ids(value["experiment_ids"], "claim.experiment_ids")
    _optional_strings(value, "claim", ("notes",))
    return value


def validate_experiment(value: dict[str, Any]) -> dict[str, Any]:
    ensure_id(value.get("id"), "experiment.id")
    ensure_id(value.get("paper_id"), "experiment.paper_id")
    ensure_text(value.get("name"), "experiment.name")
    ensure_text(value.get("protocol_summary"), "experiment.protocol_summary")
    for field in ("resource_ids", "metric_ids", "baseline_ids"):
        if field in value:
            _list_of_ids(value[field], f"experiment.{field}")
    _optional_strings(value, "experiment", ("notes",))
    return value


def validate_resource(value: dict[str, Any]) -> dict[str, Any]:
    ensure_id(value.get("id"), "resource.id")
    ensure_text(value.get("name"), "resource.name")
    _choice(value.get("kind"), RESOURCE_KINDS, "resource.kind")
    _choice(
        value.get("availability", "unknown"),
        {"available", "partial", "unavailable", "unknown"},
        "resource.availability",
    )
    _optional_strings(value, "resource", ("url", "version", "license", "checksum", "notes"))
    return value


def validate_assessment(value: dict[str, Any]) -> dict[str, Any]:
    ensure_id(value.get("id"), "assessment.id")
    ensure_id(value.get("paper_id"), "assessment.paper_id")
    kind = _choice(
        value.get("kind", "individual"),
        {"individual", "consensus"},
        "assessment.kind",
    )
    if "reviewer" in value:
        ensure_text(value["reviewer"], "assessment.reviewer")
    if "assessed_at" in value:
        ensure_text(value["assessed_at"], "assessment.assessed_at")
    if "notes" in value and not isinstance(value["notes"], str):
        raise ValidationError("assessment.notes must be a string")
    sources = (
        _list_of_ids(value["source_assessment_ids"], "assessment.source_assessment_ids")
        if "source_assessment_ids" in value
        else []
    )
    source_hashes = value.get("source_assessment_hashes")
    if kind == "individual" and (
        "source_assessment_ids" in value or "source_assessment_hashes" in value
    ):
        raise ValidationError("individual assessment cannot declare consensus source fields")
    if kind == "consensus":
        if len(sources) < 2:
            raise ValidationError("consensus assessment requires at least two source assessments")
        if len(sources) != len(set(sources)):
            raise ValidationError("consensus source_assessment_ids must be unique")
        if value["id"] in sources:
            raise ValidationError("consensus assessment cannot reference itself")
        if not isinstance(source_hashes, dict):
            raise ValidationError("consensus assessment requires source_assessment_hashes")
        if set(source_hashes) != set(sources):
            raise ValidationError(
                "consensus source hashes must cover exactly the source assessments"
            )
        for source_id, digest in source_hashes.items():
            ensure_id(source_id, "assessment.source_assessment_hashes key")
            if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
                raise ValidationError("consensus source hashes must be sha256 digests")
    ratings = value.get("ratings")
    if not isinstance(ratings, dict):
        raise ValidationError("assessment.ratings must be an object")
    unknown = set(ratings) - set(ASSESSMENT_DIMENSIONS)
    if unknown:
        raise ValidationError(f"unknown assessment dimensions: {', '.join(sorted(unknown))}")
    for dimension, detail in ratings.items():
        if not isinstance(detail, dict):
            raise ValidationError(f"assessment.ratings.{dimension} must be an object")
        if not isinstance(detail.get("rating"), str) or detail["rating"] not in RATING_VALUES:
            raise ValidationError(f"invalid rating for {dimension}")
        ensure_text(detail.get("evidence"), f"assessment.ratings.{dimension}.evidence")
        if "next_action" in detail and not isinstance(detail["next_action"], str):
            raise ValidationError(f"assessment.ratings.{dimension}.next_action must be a string")
    return value


def validate_task(value: dict[str, Any]) -> dict[str, Any]:
    ensure_id(value.get("id"), "task.id")
    ensure_text(value.get("title"), "task.title")
    _choice(value.get("state", "ready"), TASK_STATES, "task.state")
    _choice(value.get("priority", "medium"), TASK_PRIORITIES, "task.priority")
    if "depends_on" in value:
        _list_of_ids(value["depends_on"], "task.depends_on")
    if "paper_ids" in value:
        _list_of_ids(value["paper_ids"], "task.paper_ids")
    estimate = value.get("estimate_hours", 0)
    if (
        isinstance(estimate, bool)
        or not isinstance(estimate, (int, float))
        or (isinstance(estimate, float) and not math.isfinite(estimate))
        or estimate < 0
        or estimate > MAX_ESTIMATE_HOURS
    ):
        raise ValidationError(
            f"task.estimate_hours must be a finite number from 0 to {MAX_ESTIMATE_HOURS}"
        )
    _optional_strings(value, "task", ("acceptance", "blocker"))
    return value


def validate_screening(value: dict[str, Any]) -> dict[str, Any]:
    ensure_id(value.get("id"), "screening.id")
    ensure_id(value.get("paper_id"), "screening.paper_id")
    _choice(value.get("state"), SCREENING_STATES, "screening.state")
    ensure_text(value.get("reason"), "screening.reason")
    ensure_text(value.get("recorded_at"), "screening.recorded_at")
    _optional_strings(value, "screening", ("reviewer",))
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

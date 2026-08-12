"""Atomic, deterministic artifact storage."""

from __future__ import annotations

import json
import math
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .util import filesystem_path, pretty_json


def _reject_non_finite(value: str) -> None:
    raise ValidationError(f"non-finite number {value!r} is not valid standard JSON")


def _parse_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        _reject_non_finite(value)
    return parsed


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValidationError(f"duplicate JSON object key {key!r}")
        value[key] = item
    return value


def _validate_unicode(value: Any) -> None:
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValidationError("JSON strings must contain valid Unicode scalar values") from exc
    elif isinstance(value, dict):
        for key, item in value.items():
            _validate_unicode(key)
            _validate_unicode(item)
    elif isinstance(value, list):
        for item in value:
            _validate_unicode(item)


def parse_json_value(text: str, *, label: str = "JSON") -> Any:
    """Parse strict standard JSON while preserving arrays for import formats."""
    try:
        value = json.loads(
            text,
            parse_constant=_reject_non_finite,
            parse_float=_parse_finite_float,
            object_pairs_hook=_unique_object,
        )
        _validate_unicode(value)
        return value
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid {label}: {exc}") from exc
    except (RecursionError, ValueError) as exc:
        raise ValidationError(f"invalid {label}: {exc}") from exc
    except UnicodeError as exc:
        raise ValidationError(f"invalid {label}: {exc}") from exc
    except ValidationError as exc:
        raise ValidationError(f"invalid {label}: {exc}") from exc


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object with a useful path-aware error."""
    try:
        with open(filesystem_path(path), encoding="utf-8") as handle:
            text = handle.read()
    except FileNotFoundError as exc:
        raise ValidationError(f"missing file: {path}") from exc
    except OSError as exc:
        raise ValidationError(f"cannot read JSON file {path}: {exc}") from exc
    except UnicodeError as exc:
        raise ValidationError(f"invalid UTF-8 in {path}: {exc}") from exc
    value = parse_json_value(text, label=f"JSON in {path}")
    if not isinstance(value, dict):
        raise ValidationError(f"expected a JSON object in {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Atomically replace a JSON artifact."""
    os.makedirs(filesystem_path(path.parent), exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".reproweave-",
        suffix=".tmp",
        dir=filesystem_path(path.parent),
        text=True,
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(pretty_json(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(filesystem_path(temporary_path), filesystem_path(path))
    finally:
        if os.path.exists(filesystem_path(temporary_path)):
            os.unlink(filesystem_path(temporary_path))


def load_directory(path: Path) -> list[dict[str, Any]]:
    """Load every JSON object in filename order."""
    if not os.path.exists(filesystem_path(path)):
        return []
    with os.scandir(filesystem_path(path)) as entries:
        files = sorted(path / entry.name for entry in entries if entry.name.endswith(".json"))
    return [read_json(item) for item in files]


def write_jsonl(path: Path, values: Iterable[dict[str, Any]]) -> None:
    """Write deterministic JSON Lines content atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) for value in values
    ]
    with open(filesystem_path(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + ("\n" if lines else ""))

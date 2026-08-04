"""Atomic, deterministic artifact storage."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .util import pretty_json


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object with a useful path-aware error."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"expected a JSON object in {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Atomically replace a JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(pretty_json(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def load_directory(path: Path) -> list[dict[str, Any]]:
    """Load every JSON object in filename order."""
    if not path.exists():
        return []
    return [read_json(item) for item in sorted(path.glob("*.json"))]


def write_jsonl(path: Path, values: Iterable[dict[str, Any]]) -> None:
    """Write deterministic JSON Lines content atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(value, ensure_ascii=False, sort_keys=True) for value in values]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")

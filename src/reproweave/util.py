"""Small deterministic utilities."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import ValidationError

ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


def utc_now() -> str:
    """Return an RFC 3339 UTC timestamp without platform-specific formatting."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_id(value: str, field: str = "id") -> str:
    """Validate a portable, URL-safe identifier."""
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ValidationError(
            f"{field} must start with a lowercase letter and contain only "
            "lowercase letters, digits, and hyphens"
        )
    return value


def ensure_text(value: Any, field: str) -> str:
    """Validate a non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be a non-empty string")
    return value.strip()


def canonical_json(value: Any) -> str:
    """Serialize JSON deterministically for reviewable diffs and hashes."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def pretty_json(value: Any) -> str:
    """Serialize stable human-readable JSON."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def sha256_text(value: str) -> str:
    """Return a prefixed SHA-256 digest."""
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash a file without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def slugify(value: str) -> str:
    """Create a conservative artifact identifier from a title."""
    result = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    result = re.sub(r"-+", "-", result)
    if not result or not result[0].isalpha():
        result = f"item-{result}" if result else "item"
    return result[:80].rstrip("-")


def html_escape(value: Any) -> str:
    """Escape values inserted into the generated report."""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )

"""Workspace lifecycle and artifact access."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .constants import ARTIFACT_KINDS, FORMAT_VERSION
from .errors import ValidationError
from .models import validate
from .store import read_json, write_json
from .util import ensure_id, ensure_text, utc_now

DIRECTORIES = {
    "paper": "papers",
    "claim": "claims",
    "experiment": "experiments",
    "resource": "resources",
    "assessment": "assessments",
    "task": "tasks",
    "screening": "screening",
}


class Workspace:
    """A file-native ReproWeave project."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    @property
    def manifest_path(self) -> Path:
        return self.root / "reproweave.json"

    @classmethod
    def create(
        cls,
        root: str | Path,
        *,
        title: str,
        research_question: str,
        owner: str = "",
        overwrite: bool = False,
    ) -> Workspace:
        """Create a deterministic directory layout."""
        workspace = cls(root)
        if workspace.manifest_path.exists() and not overwrite:
            raise ValidationError(f"workspace already exists: {workspace.root}")
        workspace.root.mkdir(parents=True, exist_ok=True)
        for directory in DIRECTORIES.values():
            (workspace.root / directory).mkdir(exist_ok=True)
        (workspace.root / "reports").mkdir(exist_ok=True)
        manifest = {
            "format_version": FORMAT_VERSION,
            "title": ensure_text(title, "title"),
            "research_question": ensure_text(research_question, "research_question"),
            "owner": owner,
            "created_at": utc_now(),
            "description": "",
            "inclusion_criteria": [],
            "exclusion_criteria": [],
            "tags": [],
        }
        write_json(workspace.manifest_path, manifest)
        return workspace

    def manifest(self) -> dict[str, Any]:
        """Load and minimally validate workspace metadata."""
        manifest = read_json(self.manifest_path)
        if manifest.get("format_version") != FORMAT_VERSION:
            raise ValidationError(f"unsupported format_version: {manifest.get('format_version')!r}")
        ensure_text(manifest.get("title"), "title")
        ensure_text(manifest.get("research_question"), "research_question")
        return manifest

    def require(self) -> Workspace:
        """Fail early when a path is not a structurally valid ReproWeave workspace."""
        self.manifest()
        self.validate_integrity()
        return self

    def artifact_paths(self, kind: str) -> list[Path]:
        """List source files for one artifact kind in stable filename order."""
        if kind not in DIRECTORIES:
            raise ValidationError(f"unknown artifact kind: {kind}")
        directory = self.root / DIRECTORIES[kind]
        try:
            if not directory.exists():
                return []
            if not directory.is_dir():
                raise ValidationError(f"artifact path for {kind} must be a directory: {directory}")
            return sorted(
                item for item in directory.iterdir() if item.name.casefold().endswith(".json")
            )
        except OSError as exc:
            raise ValidationError(
                f"cannot enumerate artifact directory {directory}: {exc}"
            ) from exc

    def path_for(self, kind: str, artifact_id: str) -> Path:
        """Resolve a validated artifact path."""
        if kind not in DIRECTORIES:
            raise ValidationError(f"unknown artifact kind: {kind}")
        return self.root / DIRECTORIES[kind] / f"{ensure_id(artifact_id)}.json"

    def add(
        self,
        kind: str,
        artifact: dict[str, Any],
        *,
        replace: bool = False,
    ) -> Path:
        """Validate and write one artifact."""
        self.require()
        validated = validate(kind, artifact)
        for other_kind in DIRECTORIES:
            if other_kind != kind and self.path_for(other_kind, validated["id"]).exists():
                raise ValidationError(
                    f"artifact id {validated['id']!r} is already used by {other_kind}"
                )
        path = self.path_for(kind, validated["id"])
        if path.exists() and not replace:
            raise ValidationError(f"{kind} already exists: {validated['id']}")
        write_json(path, validated)
        return path

    def get(self, kind: str, artifact_id: str) -> dict[str, Any]:
        """Read and validate one artifact."""
        value = read_json(self.path_for(kind, artifact_id))
        return validate(kind, value)

    def all(self, kind: str) -> list[dict[str, Any]]:
        """Read and validate a kind in stable ID order."""
        if kind not in DIRECTORIES:
            raise ValidationError(f"unknown artifact kind: {kind}")
        validated = []
        seen: dict[str, Path] = {}
        for path in self.artifact_paths(kind):
            if path.suffix != ".json":
                raise ValidationError(
                    f"{kind} filename {path.name!r} must end with lowercase .json"
                )
            item = validate(kind, read_json(path))
            artifact_id = item["id"]
            if path.stem != artifact_id:
                raise ValidationError(
                    f"{kind} filename {path.name!r} does not match artifact id {artifact_id!r}"
                )
            if artifact_id in seen:
                raise ValidationError(
                    f"duplicate {kind} id {artifact_id!r} in {seen[artifact_id].name} and {path.name}"
                )
            seen[artifact_id] = path
            validated.append(item)
        return sorted(validated, key=lambda item: item["id"])

    def validate_integrity(self) -> None:
        """Enforce filename and workspace-wide identity invariants."""
        seen: dict[str, str] = {}
        for kind in DIRECTORIES:
            for item in self.all(kind):
                artifact_id = item["id"]
                if artifact_id in seen:
                    raise ValidationError(
                        f"artifact id {artifact_id!r} is reused by {seen[artifact_id]} and {kind}"
                    )
                seen[artifact_id] = kind

    def index(self, kind: str) -> dict[str, dict[str, Any]]:
        """Return artifacts keyed by ID."""
        return {item["id"]: item for item in self.all(kind)}

    def counts(self) -> dict[str, int]:
        """Count every artifact kind."""
        return {kind: len(self.all(kind)) for kind in ARTIFACT_KINDS}

    def add_many(
        self,
        kind: str,
        artifacts: Iterable[dict[str, Any]],
        *,
        replace: bool = False,
    ) -> list[Path]:
        """Add a sequence while preserving input order."""
        return [self.add(kind, item, replace=replace) for item in artifacts]

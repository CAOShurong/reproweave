"""Workspace lifecycle and artifact access."""

from __future__ import annotations

import copy
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import ARTIFACT_KINDS, FORMAT_VERSION
from .duplicates import build_duplicate_report
from .errors import ValidationError
from .models import validate
from .store import read_json, write_json
from .util import canonical_json, ensure_id, ensure_text, pretty_json, sha256_text, utc_now

DIRECTORIES = {
    "paper": "papers",
    "claim": "claims",
    "experiment": "experiments",
    "resource": "resources",
    "assessment": "assessments",
    "task": "tasks",
    "screening": "screening",
}


@dataclass(frozen=True)
class ImportPlan:
    """A fully validated batch that has not yet written to the workspace."""

    kind: str
    artifacts: tuple[dict[str, Any], ...]
    paths: tuple[Path, ...]
    candidates: tuple[dict[str, Any], ...]
    blocked_candidates: tuple[dict[str, Any], ...]
    accepted_candidate_ids: tuple[str, ...]
    workspace_root: Path
    replace: bool
    fingerprint: str

    @property
    def ready(self) -> bool:
        return not self.blocked_candidates

    def report(self, *, dry_run: bool) -> dict[str, Any]:
        """Return deterministic machine-readable preflight output."""
        return {
            "report_version": 1,
            "status": "ready" if self.ready else "blocked",
            "dry_run": dry_run,
            "would_import": len(self.artifacts),
            "paper_ids": sorted(artifact["id"] for artifact in self.artifacts),
            "accepted_candidate_ids": list(self.accepted_candidate_ids),
            "issues": [
                {
                    "code": "duplicate_candidate",
                    "candidate_id": candidate["candidate_id"],
                }
                for candidate in self.blocked_candidates
            ],
            "candidates": list(self.candidates),
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
        accepted_candidate_ids: Iterable[str] = (),
    ) -> Path:
        """Validate and write one artifact."""
        if kind == "paper":
            return self.add_many(
                kind,
                [artifact],
                replace=replace,
                accepted_candidate_ids=accepted_candidate_ids,
            )[0]
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
        accepted_candidate_ids: Iterable[str] = (),
    ) -> list[Path]:
        """Preflight a complete sequence, then write it in input order."""
        plan = self.preflight_many(
            kind,
            artifacts,
            replace=replace,
            accepted_candidate_ids=accepted_candidate_ids,
        )
        return self._commit_many(plan)

    def preflight_many(
        self,
        kind: str,
        artifacts: Iterable[dict[str, Any]],
        *,
        replace: bool = False,
        accepted_candidate_ids: Iterable[str] = (),
    ) -> ImportPlan:
        """Validate every discoverable batch error before writing any artifact."""
        self.require()
        if kind not in DIRECTORIES:
            raise ValidationError(f"unknown artifact kind: {kind}")
        validated: list[dict[str, Any]] = []
        seen_batch_ids: set[str] = set()
        for artifact in artifacts:
            item = validate(kind, copy.deepcopy(artifact))
            artifact_id = item["id"]
            if artifact_id in seen_batch_ids:
                raise ValidationError(f"duplicate {kind} id in import batch: {artifact_id!r}")
            seen_batch_ids.add(artifact_id)
            try:
                pretty_json(item).encode("utf-8")
            except (TypeError, ValueError, UnicodeError) as exc:
                raise ValidationError(
                    f"{kind} {artifact_id!r} cannot be serialized as standard UTF-8 JSON: {exc}"
                ) from exc
            validated.append(item)

        workspace_ids: dict[str, str] = {}
        for existing_kind in DIRECTORIES:
            for existing in self.all(existing_kind):
                workspace_ids[existing["id"]] = existing_kind
        for item in validated:
            existing_kind = workspace_ids.get(item["id"])
            if existing_kind is None:
                continue
            if existing_kind != kind:
                raise ValidationError(
                    f"artifact id {item['id']!r} is already used by {existing_kind}"
                )
            if not replace:
                raise ValidationError(
                    f"{kind} id {item['id']!r} already exists; incoming batch was not written"
                )

        candidate_groups: list[dict[str, Any]] = []
        if kind == "paper" and validated:
            replacement_ids = {item["id"] for item in validated} if replace else set()
            existing_papers = [
                paper for paper in self.all("paper") if paper["id"] not in replacement_ids
            ]
            duplicate_report = build_duplicate_report([*existing_papers, *validated])
            incoming_ids = {item["id"] for item in validated}
            candidate_groups = [
                candidate
                for candidate in duplicate_report["candidates"]
                if incoming_ids.intersection(candidate["paper_ids"])
            ]

        available_candidate_ids = {candidate["candidate_id"] for candidate in candidate_groups}
        accepted = tuple(sorted(set(accepted_candidate_ids)))
        unknown = sorted(set(accepted) - available_candidate_ids)
        if unknown:
            raise ValidationError(
                "accepted duplicate candidate is absent from this preflight: " + ", ".join(unknown)
            )
        blocked = tuple(
            candidate for candidate in candidate_groups if candidate["candidate_id"] not in accepted
        )
        paths = tuple(self.path_for(kind, item["id"]) for item in validated)
        fingerprint = self._plan_fingerprint(
            kind=kind,
            artifacts=validated,
            paths=paths,
            accepted_candidate_ids=accepted,
            replace=replace,
        )
        return ImportPlan(
            kind=kind,
            artifacts=tuple(validated),
            paths=paths,
            candidates=tuple(candidate_groups),
            blocked_candidates=blocked,
            accepted_candidate_ids=accepted,
            workspace_root=self.root,
            replace=replace,
            fingerprint=fingerprint,
        )

    @staticmethod
    def _plan_fingerprint(
        *,
        kind: str,
        artifacts: Iterable[dict[str, Any]],
        paths: Iterable[Path],
        accepted_candidate_ids: Iterable[str],
        replace: bool,
    ) -> str:
        return sha256_text(
            canonical_json(
                {
                    "kind": kind,
                    "artifacts": list(artifacts),
                    "paths": [str(path) for path in paths],
                    "accepted_candidate_ids": list(accepted_candidate_ids),
                    "replace": replace,
                }
            )
        )

    def _commit_many(self, plan: ImportPlan) -> list[Path]:
        """Recheck and write an internal plan without exposing a stale public commit API."""
        if plan.workspace_root != self.root:
            raise ValidationError("import plan belongs to a different workspace")
        actual_fingerprint = self._plan_fingerprint(
            kind=plan.kind,
            artifacts=plan.artifacts,
            paths=plan.paths,
            accepted_candidate_ids=plan.accepted_candidate_ids,
            replace=plan.replace,
        )
        if actual_fingerprint != plan.fingerprint:
            raise ValidationError("import plan changed after preflight; run preflight again")
        if not plan.ready:
            candidate_ids = ", ".join(
                candidate["candidate_id"] for candidate in plan.blocked_candidates
            )
            raise ValidationError(
                f"duplicate candidates require explicit acceptance: {candidate_ids}"
            )
        fresh = self.preflight_many(
            plan.kind,
            copy.deepcopy(plan.artifacts),
            replace=plan.replace,
            accepted_candidate_ids=plan.accepted_candidate_ids,
        )
        for path, artifact in zip(fresh.paths, fresh.artifacts, strict=True):
            write_json(path, artifact)
        return list(fresh.paths)

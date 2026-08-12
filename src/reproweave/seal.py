"""Content-addressed evidence seals."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .constants import ARTIFACT_KINDS
from .store import read_json, write_json
from .util import canonical_json, filesystem_path, sha256_file, sha256_text, utc_now
from .workspace import Workspace


def build_seal(workspace: Workspace) -> dict[str, Any]:
    """Hash the manifest and every source artifact, excluding generated reports."""
    files = [workspace.manifest_path]
    for kind in ARTIFACT_KINDS:
        files.extend(workspace.artifact_paths(kind))
    entries = [
        {
            "path": path.relative_to(workspace.root).as_posix(),
            "sha256": sha256_file(path),
            "bytes": os.path.getsize(filesystem_path(path)),
        }
        for path in sorted(set(files))
    ]
    root = sha256_text(canonical_json(entries))
    return {
        "algorithm": "sha256",
        "root": root,
        "file_count": len(entries),
        "files": entries,
    }


def write_seal(
    workspace: Workspace,
    path: str | Path | None = None,
    *,
    created_at: str | None = None,
) -> Path:
    """Write a seal with an informational creation timestamp."""
    destination = Path(path) if path else workspace.root / "reproweave-seal.json"
    seal = build_seal(workspace)
    seal["created_at"] = created_at or utc_now()
    write_json(destination, seal)
    return destination


def verify_seal(workspace: Workspace, path: str | Path | None = None) -> dict[str, Any]:
    """Verify the current source artifacts against a saved seal."""
    destination = Path(path) if path else workspace.root / "reproweave-seal.json"
    expected = read_json(destination)
    observed = build_seal(workspace)
    return {
        "status": "verified" if expected.get("root") == observed["root"] else "changed",
        "expected_root": expected.get("root"),
        "observed_root": observed["root"],
        "expected_file_count": expected.get("file_count"),
        "observed_file_count": observed["file_count"],
    }

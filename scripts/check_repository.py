"""Repository-level release checks beyond unit behavior."""

from __future__ import annotations

import re
import struct
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reproweave import __version__  # noqa: E402
from reproweave.audit import audit_workspace  # noqa: E402
from reproweave.constants import APP_VERSION  # noqa: E402
from reproweave.demo import create_demo  # noqa: E402
from reproweave.seal import verify_seal  # noqa: E402
from reproweave.triage import build_replication_triage  # noqa: E402
from reproweave.workspace import Workspace  # noqa: E402

EXPECTED_VERSION = "0.3.0"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_versions() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    require(__version__ == EXPECTED_VERSION, "package version mismatch")
    require(APP_VERSION == EXPECTED_VERSION, "application version mismatch")
    require(
        pyproject["project"]["version"] == EXPECTED_VERSION,
        "pyproject version mismatch",
    )
    require(f"version: {EXPECTED_VERSION}" in citation, "citation version mismatch")
    require(f"## [{EXPECTED_VERSION}]" in changelog, "changelog release missing")
    require(
        pyproject["project"]["authors"] == [{"name": "Shurong Cao"}],
        "package authorship must name Shurong Cao only",
    )


def check_install_claims() -> None:
    for relative in ("README.md", "site/index.html"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        require(
            "python -m pip install reproweave" in text,
            f"{relative} lacks the verified PyPI install path",
        )


def check_figures() -> None:
    for relative in (
        "docs/assets/hero.svg",
        "docs/assets/workflow.svg",
        "docs/assets/candidate-comparison.svg",
    ):
        path = ROOT / relative
        root = ET.fromstring(path.read_text(encoding="utf-8"))
        require(root.tag.endswith("svg"), f"{relative} is not SVG")
        require(root.get("viewBox") is not None, f"{relative} lacks a viewBox")
        text = path.read_text(encoding="utf-8")
        require("linearGradient" not in text, f"{relative} uses a gradient")
        require("<filter" not in text, f"{relative} uses a decorative filter")
    preview = ROOT / "site" / "social-preview.png"
    require(preview.is_file(), "social preview is missing")
    payload = preview.read_bytes()
    require(payload[:8] == b"\x89PNG\r\n\x1a\n", "social preview is not PNG")
    require(
        struct.unpack(">II", payload[16:24]) == (1280, 640),
        "social preview must be 1280x640",
    )


def check_relative_readme_links() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme)
    for target in targets:
        if "://" in target or target.startswith("#"):
            continue
        path_text = target.split("#", 1)[0]
        if not path_text:
            continue
        require((ROOT / path_text).exists(), f"README link target is missing: {target}")


def check_committed_demo() -> None:
    workspace = Workspace(ROOT / "examples" / "demo").require()
    audit = audit_workspace(workspace)
    verification = verify_seal(workspace)
    triage = build_replication_triage(workspace)
    require(audit["status"] == "pass", "committed demo audit failed")
    require(verification["status"] == "verified", "committed demo seal changed")
    require(len(triage["candidates"]) == workspace.counts()["paper"], "triage omits papers")
    for relative in (
        "reports/agreement.json",
        "reports/reviewer-agreement.csv",
        "reports/reviewer-agreement.md",
    ):
        require((workspace.root / relative).is_file(), f"demo output missing: {relative}")
    report = (workspace.root / "reports" / "evidence-report.html").read_text(encoding="utf-8")
    require("Replication candidate triage" in report, "demo report lacks triage")
    require("Reviewer agreement" in report, "demo report lacks agreement status")
    require("<script src=" not in report, "demo report loads an external script")
    require('rel="stylesheet"' not in report, "demo report loads an external stylesheet")
    deterministic_reports = (
        "agreement.json",
        "assessment.json",
        "evidence-graph.json",
        "evidence-matrix.csv",
        "replication-plan.md",
        "replication-triage.json",
        "replication-triage.md",
        "reviewer-agreement.csv",
        "reviewer-agreement.md",
    )
    with tempfile.TemporaryDirectory() as directory:
        generated = create_demo(Path(directory) / "demo")
        for name in deterministic_reports:
            require(
                (workspace.root / "reports" / name).read_bytes()
                == (generated.root / "reports" / name).read_bytes(),
                f"committed demo output is stale: reports/{name}",
            )


def check_workflow_action_pins() -> None:
    for workflow in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for line_number, line in enumerate(workflow.read_text(encoding="utf-8").splitlines(), 1):
            match = re.search(r"\buses:\s+[^\s]+@([^\s#]+)", line)
            if match:
                require(
                    re.fullmatch(r"[0-9a-f]{40}", match.group(1)) is not None,
                    f"{workflow.relative_to(ROOT)}:{line_number} action is not SHA-pinned",
                )


def check_workflow_release_gates() -> None:
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    pages = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    require("GITHUB_REF_NAME" in release, "release workflow does not inspect the pushed tag")
    require(
        "pyproject.toml" in release, "release workflow does not bind the tag to package metadata"
    )
    require(
        'expected = f"v{version}"' in release, "release workflow lacks an exact version tag gate"
    )
    require(
        "workflow_dispatch" not in pages, "Pages publication must not bypass successful main CI"
    )
    require(
        "workflow_run.event == 'push'" in pages,
        "Pages workflow must reject pull-request workflow_run payloads",
    )
    require(
        "workflow_run.head_repository.full_name == github.repository" in pages,
        "Pages workflow must only execute a trusted repository commit",
    )


def main() -> None:
    check_versions()
    check_install_claims()
    check_figures()
    check_relative_readme_links()
    check_committed_demo()
    check_workflow_action_pins()
    check_workflow_release_gates()
    print("repository checks: pass")


if __name__ == "__main__":
    main()

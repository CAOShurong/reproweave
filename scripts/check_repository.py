"""Repository-level release checks beyond unit behavior."""

from __future__ import annotations

import re
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reproweave import __version__  # noqa: E402
from reproweave.audit import audit_workspace  # noqa: E402
from reproweave.constants import APP_VERSION  # noqa: E402
from reproweave.seal import verify_seal  # noqa: E402
from reproweave.triage import build_replication_triage  # noqa: E402
from reproweave.workspace import Workspace  # noqa: E402

EXPECTED_VERSION = "0.2.0"


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


def check_install_claims() -> None:
    release_url = (
        "https://github.com/CAOShurong/reproweave/releases/download/"
        f"v{EXPECTED_VERSION}/reproweave-{EXPECTED_VERSION}-py3-none-any.whl"
    )
    for relative in ("README.md", "site/index.html"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        require(release_url in text, f"{relative} lacks the versioned release wheel")
        require(
            "python -m pip install reproweave" not in text,
            f"{relative} makes an unsupported PyPI install claim",
        )


def check_figures() -> None:
    for relative in ("docs/assets/hero.svg", "docs/assets/workflow.svg"):
        path = ROOT / relative
        root = ET.fromstring(path.read_text(encoding="utf-8"))
        require(root.tag.endswith("svg"), f"{relative} is not SVG")
        require(root.get("viewBox") is not None, f"{relative} lacks a viewBox")
        text = path.read_text(encoding="utf-8")
        require("linearGradient" not in text, f"{relative} uses a gradient")
        require("<filter" not in text, f"{relative} uses a decorative filter")


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
    report = (workspace.root / "reports" / "evidence-report.html").read_text(encoding="utf-8")
    require("Replication candidate triage" in report, "demo report lacks triage")
    require("<script src=" not in report, "demo report loads an external script")
    require('rel="stylesheet"' not in report, "demo report loads an external stylesheet")


def main() -> None:
    check_versions()
    check_install_claims()
    check_figures()
    check_relative_readme_links()
    check_committed_demo()
    print("repository checks: pass")


if __name__ == "__main__":
    main()

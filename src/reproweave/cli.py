"""Command-line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from . import __version__
from .audit import audit_workspace
from .bibliography import load_bibtex, load_csl_json
from .demo import create_demo
from .errors import ReproWeaveError
from .exports import matrix_csv, plan_markdown, triage_csv, triage_markdown
from .graph import build_evidence_graph
from .planning import build_replication_plan, readiness_backlog
from .report import build_report
from .scoring import assess_workspace, evidence_matrix
from .seal import verify_seal, write_seal
from .store import read_json
from .triage import build_replication_triage, parse_resource_overrides
from .util import pretty_json
from .workspace import Workspace


def _workspace(args: argparse.Namespace) -> Workspace:
    return Workspace(args.workspace).require()


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reproweave",
        description="Build auditable evidence maps and replication plans without an API.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="create an empty workspace")
    init.add_argument("workspace")
    init.add_argument("--title", required=True)
    init.add_argument("--question", required=True)
    init.add_argument("--owner", default="")

    add = subparsers.add_parser("add", help="add a validated artifact from JSON")
    add.add_argument(
        "kind",
        choices=("paper", "claim", "experiment", "resource", "assessment", "task", "screening"),
    )
    add.add_argument("json_file")
    add.add_argument("--workspace", "-w", default=".")
    add.add_argument("--replace", action="store_true")

    import_parser = subparsers.add_parser("import", help="import bibliography records")
    import_parser.add_argument("format", choices=("bibtex", "csl-json"))
    import_parser.add_argument("source")
    import_parser.add_argument("--workspace", "-w", default=".")
    import_parser.add_argument("--replace", action="store_true")

    for name, help_text in (
        ("assess", "compute transparent reconstructability scores"),
        ("matrix", "export the paper-by-evidence matrix"),
        ("plan", "build dependency-aware replication waves"),
        ("backlog", "list unresolved evidence-gathering work"),
        ("triage", "rank replication candidates using explicit execution rules"),
        ("graph", "export the typed evidence graph"),
        ("audit", "validate artifacts and cross references"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--workspace", "-w", default=".")
        if name in {"matrix", "plan", "triage"}:
            command.add_argument("--format", choices=("json", "csv", "markdown"), default="json")
        if name == "triage":
            command.add_argument(
                "--resource",
                action="append",
                default=[],
                metavar="ID=AVAILABILITY",
                help="override one resource for a what-if scenario; repeat as needed",
            )
        command.add_argument("--output", "-o")

    report = subparsers.add_parser("report", help="generate a self-contained HTML report")
    report.add_argument("--workspace", "-w", default=".")
    report.add_argument("--output", "-o", default="reports/evidence-report.html")

    seal = subparsers.add_parser("seal", help="write a content-addressed evidence seal")
    seal.add_argument("--workspace", "-w", default=".")
    seal.add_argument("--output", "-o")

    verify = subparsers.add_parser("verify", help="verify a saved evidence seal")
    verify.add_argument("--workspace", "-w", default=".")
    verify.add_argument("--seal")

    demo = subparsers.add_parser("demo", help="create the synthetic EE/AI demonstration")
    demo.add_argument("workspace")
    demo.add_argument("--force", action="store_true")
    return parser


def _emit(value: str, output: str | None) -> None:
    if output:
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(value, encoding="utf-8", newline="\n")
        print(destination.resolve())
    else:
        print(value, end="" if value.endswith("\n") else "\n")


def run(args: argparse.Namespace) -> int:
    """Execute a parsed command and return an exit code."""
    if args.command == "init":
        workspace = Workspace.create(
            args.workspace, title=args.title, research_question=args.question, owner=args.owner
        )
        print(workspace.root)
        return 0
    if args.command == "demo":
        workspace = create_demo(args.workspace, force=args.force)
        _print_json({"workspace": str(workspace.root), "counts": workspace.counts()})
        return 0
    workspace = _workspace(args)
    if args.command == "add":
        path = workspace.add(args.kind, read_json(Path(args.json_file)), replace=args.replace)
        print(path)
        return 0
    if args.command == "import":
        papers = load_bibtex(args.source) if args.format == "bibtex" else load_csl_json(args.source)
        paths = workspace.add_many("paper", papers, replace=args.replace)
        _print_json({"imported": len(paths), "paper_ids": [path.stem for path in paths]})
        return 0
    if args.command == "assess":
        value = assess_workspace(workspace)
        _emit(pretty_json(value), args.output)
        return 0
    if args.command == "matrix":
        value = (
            matrix_csv(workspace)
            if args.format == "csv"
            else pretty_json(evidence_matrix(workspace))
        )
        _emit(value, args.output)
        return 0
    if args.command == "plan":
        value = (
            plan_markdown(workspace)
            if args.format == "markdown"
            else pretty_json(build_replication_plan(workspace))
        )
        _emit(value, args.output)
        return 0
    if args.command == "backlog":
        _emit(pretty_json(readiness_backlog(workspace)), args.output)
        return 0
    if args.command == "triage":
        overrides = parse_resource_overrides(args.resource)
        if args.format == "csv":
            value = triage_csv(workspace, overrides)
        elif args.format == "markdown":
            value = triage_markdown(workspace, overrides)
        else:
            value = pretty_json(build_replication_triage(workspace, overrides))
        _emit(value, args.output)
        return 0
    if args.command == "graph":
        _emit(pretty_json(build_evidence_graph(workspace)), args.output)
        return 0
    if args.command == "audit":
        result = audit_workspace(workspace)
        _emit(pretty_json(result), args.output)
        return 0 if result["status"] == "pass" else 2
    if args.command == "report":
        destination = Path(args.output)
        if not destination.is_absolute():
            destination = workspace.root / destination
        print(build_report(workspace, destination))
        return 0
    if args.command == "seal":
        destination = Path(args.output) if args.output else None
        if destination and not destination.is_absolute():
            destination = workspace.root / destination
        print(write_seal(workspace, destination))
        return 0
    if args.command == "verify":
        destination = Path(args.seal) if args.seal else None
        if destination and not destination.is_absolute():
            destination = workspace.root / destination
        result = verify_seal(workspace, destination)
        _print_json(result)
        return 0 if result["status"] == "verified" else 3
    raise AssertionError(f"unhandled command: {args.command}")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = _parser()
    try:
        code = run(parser.parse_args(argv))
    except (ReproWeaveError, FileNotFoundError, PermissionError) as exc:
        parser.exit(1, f"reproweave: error: {exc}\n")
    raise SystemExit(code)


if __name__ == "__main__":
    main()

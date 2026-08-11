"""Deterministic synthetic EE/AI literature review demonstration."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .assessments import build_assessment_resolution
from .audit import audit_workspace
from .exports import agreement_csv, agreement_markdown, matrix_csv, plan_markdown, triage_markdown
from .graph import build_evidence_graph
from .report import build_report
from .scoring import assess_workspace
from .seal import write_seal
from .store import write_json
from .triage import build_replication_triage
from .util import pretty_json
from .workspace import Workspace

DEMO_TIMESTAMP = "2026-01-15T08:00:00Z"


def _paper(
    identifier: str,
    title: str,
    authors: list[str],
    year: int,
    venue: str,
    tags: list[str],
) -> dict[str, Any]:
    return {
        "id": identifier,
        "title": title,
        "authors": authors,
        "year": year,
        "venue": venue,
        "doi": "",
        "url": "",
        "abstract": "",
        "notes": "Synthetic demonstration record; not a real publication.",
        "tags": tags,
    }


def _ratings(values: dict[str, tuple[str, str, str]]) -> dict[str, dict[str, str]]:
    return {
        dimension: {"rating": rating, "evidence": evidence, "next_action": action}
        for dimension, (rating, evidence, action) in values.items()
    }


def _assessment(
    identifier: str,
    paper_id: str,
    values: dict[str, tuple[str, str, str]],
) -> dict[str, Any]:
    return {
        "id": identifier,
        "paper_id": paper_id,
        "reviewer": "Synthetic demo reviewer",
        "assessed_at": DEMO_TIMESTAMP,
        "ratings": _ratings(values),
        "notes": "Demonstration ratings, not an evaluation of a real paper.",
    }


def _build_papers() -> list[dict[str, Any]]:
    return [
        _paper(
            "edgeformer-2025",
            "EdgeFormer: Event-Driven Transformers for On-Device RF Classification",
            ["Mira Chen", "Daniel Ortiz"],
            2025,
            "Synthetic EE/AI Systems Workshop",
            ["edge-ai", "rf", "transformers"],
        ),
        _paper(
            "sparsebeam-2024",
            "SparseBeam: Low-Overhead Beam Selection with Structured Priors",
            ["Leila Raman", "Noah Park", "Iris Wu"],
            2024,
            "Synthetic Wireless Systems Conference",
            ["wireless", "beamforming", "sparsity"],
        ),
        _paper(
            "thermaltiny-2025",
            "ThermalTiny: Calibrated TinyML under Dynamic Thermal Budgets",
            ["Arun Silva", "Mae Lewis"],
            2025,
            "Synthetic Embedded Intelligence Symposium",
            ["tinyml", "calibration", "thermal"],
        ),
        _paper(
            "channelcraft-2023",
            "ChannelCraft: A Procedural Benchmark for Robust Channel Estimation",
            ["J. Ahmed", "Sofia Kim"],
            2023,
            "Synthetic Signal Processing Letters",
            ["channel-estimation", "benchmark", "simulation"],
        ),
        _paper(
            "voltguard-2024",
            "VoltGuard: Uncertainty-Aware Fault Detection in Converter Telemetry",
            ["Priya Nair", "Evan Stone"],
            2024,
            "Synthetic Power Electronics Journal",
            ["power-electronics", "fault-detection", "uncertainty"],
        ),
    ]


def _build_resources() -> list[dict[str, Any]]:
    return [
        {
            "id": "edgeformer-code",
            "name": "EdgeFormer training repository",
            "kind": "code",
            "availability": "available",
            "url": "https://example.invalid/edgeformer",
            "version": "commit 4f91a2e (synthetic)",
            "license": "Apache-2.0",
            "notes": "Synthetic URL; demonstrates version capture.",
        },
        {
            "id": "rf-spectra-v2",
            "name": "RF Spectra v2 dataset",
            "kind": "dataset",
            "availability": "partial",
            "url": "",
            "version": "2.0",
            "license": "research-only",
            "notes": "Labels are available; raw captures are not.",
        },
        {
            "id": "a100-environment",
            "name": "CUDA training environment",
            "kind": "environment",
            "availability": "available",
            "url": "",
            "version": "container digest synthetic:91c0",
            "license": "",
            "notes": "Pinned container and seeds.",
        },
        {
            "id": "sparsebeam-code",
            "name": "SparseBeam reference scripts",
            "kind": "code",
            "availability": "partial",
            "url": "https://example.invalid/sparsebeam",
            "version": "release 0.2 (synthetic)",
            "license": "",
            "notes": "Evaluation is present; training is omitted.",
        },
        {
            "id": "mmwave-traces",
            "name": "Urban mmWave channel traces",
            "kind": "dataset",
            "availability": "unavailable",
            "url": "",
            "version": "",
            "license": "",
            "notes": "Paper states that partner restrictions prevent distribution.",
        },
        {
            "id": "thermal-board",
            "name": "Custom thermal-control evaluation board",
            "kind": "hardware",
            "availability": "partial",
            "url": "",
            "version": "rev C",
            "license": "",
            "notes": "Schematic shown; BOM and firmware are incomplete.",
        },
        {
            "id": "thermaltiny-code",
            "name": "ThermalTiny inference firmware",
            "kind": "code",
            "availability": "available",
            "url": "https://example.invalid/thermaltiny",
            "version": "tag v1.1 (synthetic)",
            "license": "MIT",
            "notes": "Training pipeline is not included.",
        },
        {
            "id": "channel-generator",
            "name": "Procedural channel generator",
            "kind": "code",
            "availability": "available",
            "url": "https://example.invalid/channelcraft",
            "version": "commit a30bf19 (synthetic)",
            "license": "BSD-3-Clause",
            "checksum": "sha256:synthetic-demo-value",
            "notes": "Generator, configs, and checksums are recorded.",
        },
        {
            "id": "channelcraft-results",
            "name": "ChannelCraft result bundle",
            "kind": "result",
            "availability": "available",
            "url": "",
            "version": "artifact set 1",
            "license": "CC-BY-4.0",
            "notes": "Per-seed CSV outputs.",
        },
        {
            "id": "converter-telemetry",
            "name": "Converter telemetry traces",
            "kind": "dataset",
            "availability": "unknown",
            "url": "",
            "version": "",
            "license": "",
            "notes": "Availability statement was not located.",
        },
        {
            "id": "voltguard-model",
            "name": "VoltGuard checkpoint",
            "kind": "model",
            "availability": "unavailable",
            "url": "",
            "version": "",
            "license": "",
            "notes": "No checkpoint link appears in the synthetic record.",
        },
    ]


def _build_experiments() -> list[dict[str, Any]]:
    return [
        {
            "id": "edgeformer-main",
            "paper_id": "edgeformer-2025",
            "name": "Main on-device RF benchmark",
            "protocol_summary": "Train five seeds and measure macro F1, latency, and energy.",
            "resource_ids": ["edgeformer-code", "rf-spectra-v2", "a100-environment"],
            "metric_ids": [],
            "baseline_ids": [],
            "notes": "Test split hash is not disclosed.",
        },
        {
            "id": "edgeformer-ablation",
            "paper_id": "edgeformer-2025",
            "name": "Event encoder ablation",
            "protocol_summary": "Replace event encoder while holding parameter count constant.",
            "resource_ids": ["edgeformer-code", "rf-spectra-v2"],
            "metric_ids": [],
            "baseline_ids": [],
        },
        {
            "id": "sparsebeam-city",
            "paper_id": "sparsebeam-2024",
            "name": "Urban beam-selection evaluation",
            "protocol_summary": "Evaluate top-k beam recall over three synthetic urban layouts.",
            "resource_ids": ["sparsebeam-code", "mmwave-traces"],
            "metric_ids": [],
            "baseline_ids": [],
        },
        {
            "id": "thermal-drift",
            "paper_id": "thermaltiny-2025",
            "name": "Temperature drift calibration",
            "protocol_summary": "Sweep board temperature from 20 to 80 C and recalibrate confidence.",
            "resource_ids": ["thermal-board", "thermaltiny-code"],
            "metric_ids": [],
            "baseline_ids": [],
        },
        {
            "id": "channelcraft-main",
            "paper_id": "channelcraft-2023",
            "name": "Procedural channel benchmark",
            "protocol_summary": "Generate 20 channel families across 10 seeds and compare six estimators.",
            "resource_ids": ["channel-generator", "channelcraft-results"],
            "metric_ids": [],
            "baseline_ids": [],
        },
        {
            "id": "voltguard-id",
            "paper_id": "voltguard-2024",
            "name": "In-distribution fault classification",
            "protocol_summary": "Evaluate AUROC and calibration error on the documented operating range.",
            "resource_ids": ["converter-telemetry", "voltguard-model"],
            "metric_ids": [],
            "baseline_ids": [],
        },
        {
            "id": "voltguard-shift",
            "paper_id": "voltguard-2024",
            "name": "Load-shift robustness",
            "protocol_summary": "Shift load profiles and evaluate selective prediction coverage.",
            "resource_ids": ["converter-telemetry", "voltguard-model"],
            "metric_ids": [],
            "baseline_ids": [],
        },
    ]


def _build_claims() -> list[dict[str, Any]]:
    rows = [
        (
            "claim-edge-f1",
            "edgeformer-2025",
            "EdgeFormer reports higher macro F1 than the compact convolutional baseline.",
            "Results §4.2, Table 2 (synthetic)",
            ["edgeformer-main"],
            "reported",
        ),
        (
            "claim-edge-energy",
            "edgeformer-2025",
            "Event gating reportedly lowers median inference energy on the target board.",
            "Results §4.3, Figure 5 (synthetic)",
            ["edgeformer-main", "edgeformer-ablation"],
            "uncertain",
        ),
        (
            "claim-beam-recall",
            "sparsebeam-2024",
            "Structured priors reportedly improve top-3 beam recall in dense layouts.",
            "Results §5, Table 1 (synthetic)",
            ["sparsebeam-city"],
            "reported",
        ),
        (
            "claim-beam-overhead",
            "sparsebeam-2024",
            "The method claims lower pilot overhead at the stated recall target.",
            "Abstract and §5.4 (synthetic)",
            ["sparsebeam-city"],
            "uncertain",
        ),
        (
            "claim-thermal-ece",
            "thermaltiny-2025",
            "Temperature-aware recalibration reportedly reduces expected calibration error.",
            "Figure 6 and Appendix B (synthetic)",
            ["thermal-drift"],
            "reported",
        ),
        (
            "claim-thermal-limit",
            "thermaltiny-2025",
            "The calibration benefit degrades outside the board's characterized range.",
            "Limitations §7 (synthetic)",
            ["thermal-drift"],
            "corroborated",
        ),
        (
            "claim-channel-robust",
            "channelcraft-2023",
            "Estimator rankings change across procedural channel families.",
            "Table 3 and artifact results.csv (synthetic)",
            ["channelcraft-main"],
            "corroborated",
        ),
        (
            "claim-channel-seeds",
            "channelcraft-2023",
            "Ten released seeds reproduce the reported aggregate within tolerance.",
            "Appendix C and result bundle (synthetic)",
            ["channelcraft-main"],
            "corroborated",
        ),
        (
            "claim-volt-auroc",
            "voltguard-2024",
            "VoltGuard reports higher in-distribution AUROC than a deterministic network.",
            "Results §4.1, Table 2 (synthetic)",
            ["voltguard-id"],
            "reported",
        ),
        (
            "claim-volt-shift",
            "voltguard-2024",
            "Selective prediction reportedly preserves precision under load shift.",
            "Results §4.4, Figure 7 (synthetic)",
            ["voltguard-shift"],
            "uncertain",
        ),
    ]
    return [
        {
            "id": identifier,
            "paper_id": paper_id,
            "statement": statement,
            "evidence_locator": locator,
            "experiment_ids": experiment_ids,
            "type": "empirical" if "limit" not in identifier else "limitation",
            "confidence": confidence,
            "notes": "Synthetic demonstration claim.",
        }
        for identifier, paper_id, statement, locator, experiment_ids, confidence in rows
    ]


def _build_assessments() -> list[dict[str, Any]]:
    y = ("yes", "Explicitly documented in the synthetic paper and artifacts.", "No action.")
    p = (
        "partial",
        "Some information is present, but one reconstruction choice remains.",
        "Record the missing choice.",
    )
    n = (
        "no",
        "The synthetic paper explicitly withholds or omits this item.",
        "Request or independently recreate it.",
    )
    u = (
        "unknown",
        "No availability statement was found in the synthetic record.",
        "Contact the authors or search supplements.",
    )
    return [
        _assessment(
            "assess-edgeformer",
            "edgeformer-2025",
            {
                "method": y,
                "data": p,
                "code": y,
                "environment": y,
                "metrics": y,
                "baselines": p,
                "compute": p,
                "results": p,
            },
        ),
        _assessment(
            "assess-sparsebeam",
            "sparsebeam-2024",
            {
                "method": p,
                "data": n,
                "code": p,
                "environment": u,
                "metrics": y,
                "baselines": p,
                "compute": u,
                "results": p,
            },
        ),
        _assessment(
            "assess-thermaltiny",
            "thermaltiny-2025",
            {
                "method": y,
                "data": p,
                "code": p,
                "environment": p,
                "metrics": y,
                "baselines": y,
                "compute": p,
                "results": p,
            },
        ),
        _assessment(
            "assess-channelcraft",
            "channelcraft-2023",
            {
                "method": y,
                "data": y,
                "code": y,
                "environment": y,
                "metrics": y,
                "baselines": y,
                "compute": y,
                "results": y,
            },
        ),
        _assessment(
            "assess-voltguard",
            "voltguard-2024",
            {
                "method": p,
                "data": u,
                "code": n,
                "environment": u,
                "metrics": y,
                "baselines": y,
                "compute": n,
                "results": p,
            },
        ),
    ]


def _build_tasks() -> list[dict[str, Any]]:
    rows = [
        ("freeze-sources", "Freeze paper and supplement versions", [], "done", "critical", 1.5),
        (
            "verify-licenses",
            "Verify code and data reuse conditions",
            ["freeze-sources"],
            "done",
            "critical",
            2,
        ),
        (
            "rebuild-channel-env",
            "Rebuild ChannelCraft environment",
            ["verify-licenses"],
            "done",
            "high",
            4,
        ),
        (
            "rerun-channel",
            "Rerun ChannelCraft released seeds",
            ["rebuild-channel-env"],
            "done",
            "high",
            6,
        ),
        (
            "acquire-rf-data",
            "Resolve RF Spectra raw-capture access",
            ["verify-licenses"],
            "blocked",
            "critical",
            3,
        ),
        (
            "train-edgeformer",
            "Train EdgeFormer across five seeds",
            ["acquire-rf-data"],
            "blocked",
            "high",
            18,
        ),
        (
            "profile-edge-energy",
            "Profile EdgeFormer board energy",
            ["train-edgeformer"],
            "blocked",
            "high",
            7,
        ),
        (
            "rebuild-thermal-board",
            "Reconstruct ThermalTiny evaluation board",
            ["verify-licenses"],
            "ready",
            "high",
            12,
        ),
        (
            "run-thermal-sweep",
            "Run the thermal calibration sweep",
            ["rebuild-thermal-board"],
            "ready",
            "medium",
            8,
        ),
        (
            "replace-mmwave-traces",
            "Design an open trace substitute for SparseBeam",
            ["verify-licenses"],
            "ready",
            "high",
            10,
        ),
        (
            "implement-sparsebeam",
            "Reconstruct missing SparseBeam training path",
            ["replace-mmwave-traces"],
            "ready",
            "medium",
            14,
        ),
        (
            "request-volt-data",
            "Resolve VoltGuard telemetry availability",
            ["freeze-sources"],
            "blocked",
            "critical",
            2,
        ),
    ]
    return [
        {
            "id": identifier,
            "title": title,
            "depends_on": dependencies,
            "paper_ids": [
                "edgeformer-2025"
                if "edge" in identifier or "rf-" in identifier
                else "channelcraft-2023"
                if "channel" in identifier
                else "thermaltiny-2025"
                if "thermal" in identifier
                else "sparsebeam-2024"
                if "sparse" in identifier or "mmwave" in identifier
                else "voltguard-2024"
                if "volt" in identifier
                else "edgeformer-2025"
            ],
            "state": state,
            "priority": priority,
            "estimate_hours": hours,
            "acceptance": f"Documented outputs satisfy the acceptance check for {title.lower()}.",
            "blocker": (
                "External data or hardware access is unresolved." if state == "blocked" else ""
            ),
        }
        for identifier, title, dependencies, state, priority, hours in rows
    ]


def create_demo(root: str | Path, *, force: bool = False) -> Workspace:
    """Create a deterministic synthetic workspace and its generated outputs."""
    root_path = Path(root).resolve()
    if root_path.exists() and any(root_path.iterdir()):
        if not force:
            raise FileExistsError(f"demo destination is not empty: {root_path}")
        shutil.rmtree(root_path)
    workspace = Workspace.create(
        root_path,
        title="Edge Intelligence Reproducibility Map",
        research_question=(
            "Which reported gains in edge intelligence can be independently reconstructed "
            "with available code, data, hardware, and result provenance?"
        ),
        owner="Synthetic demonstration",
    )
    manifest = workspace.manifest()
    manifest.update(
        {
            "created_at": DEMO_TIMESTAMP,
            "description": (
                "A completely synthetic evidence map demonstrating the ReproWeave workflow. "
                "No paper, author, URL, score, or result should be treated as real."
            ),
            "inclusion_criteria": [
                "Reports an EE or edge-AI empirical result",
                "Provides enough detail to identify at least one experiment",
            ],
            "exclusion_criteria": ["Editorials without empirical claims"],
            "tags": ["synthetic-demo", "edge-ai", "electrical-engineering"],
        }
    )
    write_json(workspace.manifest_path, manifest)
    workspace.add_many("paper", _build_papers())
    workspace.add_many("resource", _build_resources())
    workspace.add_many("experiment", _build_experiments())
    workspace.add_many("claim", _build_claims())
    workspace.add_many("assessment", _build_assessments())
    workspace.add_many("task", _build_tasks())
    workspace.add_many(
        "screening",
        [
            {
                "id": f"screen-{paper['id']}",
                "paper_id": paper["id"],
                "state": "included",
                "reason": "Meets the synthetic demonstration inclusion criteria.",
                "recorded_at": DEMO_TIMESTAMP,
                "reviewer": "Synthetic demo reviewer",
            }
            for paper in _build_papers()
        ],
    )
    reports = workspace.root / "reports"
    (reports / "evidence-matrix.csv").write_text(
        matrix_csv(workspace), encoding="utf-8", newline="\n"
    )
    (reports / "replication-plan.md").write_text(
        plan_markdown(workspace), encoding="utf-8", newline="\n"
    )
    (reports / "replication-triage.md").write_text(
        triage_markdown(workspace), encoding="utf-8", newline="\n"
    )
    (reports / "reviewer-agreement.csv").write_text(
        agreement_csv(workspace), encoding="utf-8", newline="\n"
    )
    (reports / "reviewer-agreement.md").write_text(
        agreement_markdown(workspace), encoding="utf-8", newline="\n"
    )
    for name, value in (
        ("agreement.json", build_assessment_resolution(workspace)),
        ("assessment.json", assess_workspace(workspace)),
        ("audit.json", audit_workspace(workspace)),
        ("evidence-graph.json", build_evidence_graph(workspace)),
        ("replication-triage.json", build_replication_triage(workspace)),
    ):
        (reports / name).write_text(pretty_json(value), encoding="utf-8", newline="\n")
    build_report(workspace, workspace.root / "reports" / "evidence-report.html")
    write_seal(workspace, created_at=DEMO_TIMESTAMP)
    return workspace

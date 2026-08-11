"""Deterministic, read-only bibliography duplicate candidates."""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from collections import defaultdict
from typing import Any

from .util import canonical_json, sha256_text

REPORT_VERSION = 1
NORMALIZATION_VERSION = 1

_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
)


def _normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"\s+", " ", text).strip()


def normalize_doi(value: Any) -> str:
    """Normalize only well-known DOI wrappers, preserving the identifier itself."""
    normalized = _normalize_text(value)
    for prefix in _DOI_PREFIXES:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :].strip()
            break
    return normalized


def normalize_title(value: Any) -> str:
    """Normalize Unicode, case, and whitespace for conservative title comparison."""
    return _normalize_text(value)


def normalize_author(value: Any) -> str:
    """Normalize one author label without guessing name order or identity."""
    normalized = _normalize_text(value)
    return "" if normalized == "unknown" else normalized


def _paper_summary(paper: dict[str, Any]) -> dict[str, Any]:
    authors = paper.get("authors", [])
    first_author = authors[0] if isinstance(authors, list) and authors else ""
    return {
        "paper_id": paper["id"],
        "title": paper.get("title", ""),
        "year": paper.get("year"),
        "first_author": first_author,
        "doi": paper.get("doi", ""),
        "normalized_doi": normalize_doi(paper.get("doi", "")),
        "normalized_title": normalize_title(paper.get("title", "")),
        "normalized_first_author": normalize_author(first_author),
    }


def _pair_reasons(left: dict[str, Any], right: dict[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    if left["normalized_doi"] and left["normalized_doi"] == right["normalized_doi"]:
        reasons.append("same_doi")
    left_year = left["year"]
    right_year = right["year"]
    compatible_year = (
        isinstance(left_year, int)
        and isinstance(right_year, int)
        and abs(left_year - right_year) <= 1
    )
    if (
        left["normalized_title"]
        and left["normalized_title"] == right["normalized_title"]
        and compatible_year
        and left["normalized_first_author"]
        and left["normalized_first_author"] == right["normalized_first_author"]
    ):
        reasons.append("same_title_year_author")
    return tuple(reasons)


def _edge_evidence(
    left: dict[str, Any], right: dict[str, Any], reasons: tuple[str, ...]
) -> dict[str, Any]:
    """Bind one candidate edge to the normalized evidence that produced it."""
    evidence: dict[str, Any] = {
        "paper_ids": sorted((left["paper_id"], right["paper_id"])),
        "reasons": list(reasons),
    }
    if "same_doi" in reasons:
        evidence["normalized_doi"] = left["normalized_doi"]
    if "same_title_year_author" in reasons:
        evidence.update(
            {
                "normalized_title": left["normalized_title"],
                "years": sorted((left["year"], right["year"])),
                "normalized_first_author": left["normalized_first_author"],
            }
        )
    return evidence


def build_duplicate_report(papers: list[dict[str, Any]]) -> dict[str, Any]:
    """Return stable candidate groups without mutating or resolving any paper."""
    summaries = sorted(
        (_paper_summary(paper) for paper in papers), key=lambda item: item["paper_id"]
    )
    parents = list(range(len(summaries)))
    edges: list[tuple[int, int, dict[str, Any]]] = []

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for left_index, left in enumerate(summaries):
        for right_index in range(left_index + 1, len(summaries)):
            reasons = _pair_reasons(left, summaries[right_index])
            if reasons:
                edges.append(
                    (
                        left_index,
                        right_index,
                        _edge_evidence(left, summaries[right_index], reasons),
                    )
                )
                union(left_index, right_index)

    members_by_root: dict[int, list[int]] = defaultdict(list)
    for index in range(len(summaries)):
        members_by_root[find(index)].append(index)

    groups: list[dict[str, Any]] = []
    for member_indexes in members_by_root.values():
        if len(member_indexes) < 2:
            continue
        member_set = set(member_indexes)
        group_edges = sorted(
            (
                edge
                for left_index, right_index, edge in edges
                if left_index in member_set and right_index in member_set
            ),
            key=lambda edge: (edge["paper_ids"], edge["reasons"]),
        )
        group_reasons = sorted({reason for edge in group_edges for reason in edge["reasons"]})
        members = [summaries[index] for index in member_indexes]
        paper_ids = [member["paper_id"] for member in members]
        identity = {
            "normalization_version": NORMALIZATION_VERSION,
            "papers": [
                {
                    "paper_id": member["paper_id"],
                    "normalized_doi": member["normalized_doi"],
                    "normalized_title": member["normalized_title"],
                    "normalized_first_author": member["normalized_first_author"],
                    "year": member["year"],
                }
                for member in members
            ],
            "edges": group_edges,
        }
        doi_edges = ["same_doi" in edge["reasons"] for edge in group_edges]
        confidence = "exact" if all(doi_edges) else "mixed" if any(doi_edges) else "possible"
        groups.append(
            {
                "candidate_id": sha256_text(canonical_json(identity)),
                "confidence": confidence,
                "reasons": group_reasons,
                "paper_ids": paper_ids,
                "edges": group_edges,
                "papers": members,
            }
        )
    groups.sort(key=lambda item: (item["paper_ids"], item["candidate_id"]))
    return {
        "report_version": REPORT_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "paper_count": len(summaries),
        "candidate_group_count": len(groups),
        "has_candidates": bool(groups),
        "candidates": groups,
    }


def _csv_cell(value: Any) -> Any:
    """Prevent spreadsheet applications from interpreting untrusted text as a formula."""
    if not isinstance(value, str):
        return value
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def duplicate_report_csv(report: dict[str, Any]) -> str:
    """Render one stable, spreadsheet-safe CSV row per candidate-group member."""
    fieldnames = [
        "candidate_id",
        "confidence",
        "reasons",
        "paper_id",
        "title",
        "year",
        "first_author",
        "doi",
        "normalized_doi",
        "normalized_title",
    ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for group in report["candidates"]:
        for paper in group["papers"]:
            row = {
                "candidate_id": group["candidate_id"],
                "confidence": group["confidence"],
                "reasons": ";".join(group["reasons"]),
                **{field: paper[field] for field in fieldnames[3:]},
            }
            writer.writerow({field: _csv_cell(value) for field, value in row.items()})
    return output.getvalue()


def _markdown_cell(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def duplicate_report_markdown(report: dict[str, Any]) -> str:
    """Render a deterministic, review-oriented Markdown report."""
    lines = [
        "# Bibliography duplicate candidates",
        "",
        f"Candidate groups: {report['candidate_group_count']}",
        "",
        "| Candidate | Confidence | Reasons | Paper | Title | Year | First author | DOI |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for group in report["candidates"]:
        for paper in group["papers"]:
            lines.append(
                "| "
                + " | ".join(
                    _markdown_cell(value)
                    for value in (
                        group["candidate_id"],
                        group["confidence"],
                        ", ".join(group["reasons"]),
                        paper["paper_id"],
                        paper["title"],
                        paper["year"],
                        paper["first_author"],
                        paper["doi"],
                    )
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "Candidates are evidence for review, not automatic merge or deletion decisions.",
            "",
        ]
    )
    return "\n".join(lines)

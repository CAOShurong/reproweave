"""Small offline importers for CSL JSON and a practical BibTeX subset."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .util import slugify


def _split_balanced_entries(text: str) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    cursor = 0
    while True:
        match = re.search(r"@([A-Za-z]+)\s*([\{\(])", text[cursor:])
        if not match:
            break
        kind = match.group(1).lower()
        opener = match.group(2)
        closer = "}" if opener == "{" else ")"
        start = cursor + match.end()
        depth = 1
        quoted = False
        escaped = False
        position = start
        while position < len(text) and depth:
            char = text[position]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = not quoted
            elif not quoted:
                if char == opener:
                    depth += 1
                elif char == closer:
                    depth -= 1
            position += 1
        if depth:
            raise ValidationError("unbalanced BibTeX entry")
        body = text[start : position - 1].strip()
        comma = body.find(",")
        if kind in {"comment", "preamble", "string"} and comma < 0:
            entries.append((kind, "", body))
            cursor = position
            continue
        if comma < 0:
            raise ValidationError("BibTeX entry is missing a citation key")
        key = body[:comma].strip()
        entries.append((kind, key, body[comma + 1 :]))
        cursor = position
    return entries


def _parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    cursor = 0
    while cursor < len(body):
        separator = re.match(r"\s*,?\s*", body[cursor:])
        cursor += separator.end() if separator else 0
        if cursor >= len(body):
            break
        name_match = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", body[cursor:])
        if not name_match:
            raise ValidationError(f"cannot parse BibTeX near: {body[cursor : cursor + 30]!r}")
        name = name_match.group(1).lower()
        cursor += name_match.end()
        if cursor >= len(body):
            raise ValidationError(f"missing value for BibTeX field {name}")
        if body[cursor] in '{"':
            opener = body[cursor]
            closer = "}" if opener == "{" else '"'
            cursor += 1
            start = cursor
            depth = 1 if opener == "{" else 0
            escaped = False
            while cursor < len(body):
                char = body[cursor]
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif opener == "{" and char == "{":
                    depth += 1
                elif char == closer:
                    if opener == "{":
                        depth -= 1
                        if depth == 0:
                            break
                    else:
                        break
                cursor += 1
            if cursor >= len(body):
                raise ValidationError(f"unterminated BibTeX field {name}")
            value = body[start:cursor]
            cursor += 1
        else:
            match = re.match(r"([^,\s]+)", body[cursor:])
            if not match:
                raise ValidationError(f"missing value for BibTeX field {name}")
            value = match.group(1)
            cursor += match.end()
        fields[name] = re.sub(r"\s+", " ", value).strip()
    return fields


def parse_bibtex(text: str) -> list[dict[str, Any]]:
    """Parse common BibTeX entries into ReproWeave paper records.

    Macros, crossref inheritance, and LaTeX-to-Unicode conversion are intentionally
    outside this importer's scope. Original source files should remain under version control.
    """
    papers: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry_type, key, body in _split_balanced_entries(text):
        if entry_type in {"comment", "preamble", "string"}:
            continue
        fields = _parse_fields(body)
        title = fields.get("title", "").replace("{", "").replace("}", "")
        if not title:
            raise ValidationError(f"BibTeX entry {key!r} is missing title")
        try:
            year = int(fields["year"])
        except (KeyError, ValueError) as exc:
            raise ValidationError(f"BibTeX entry {key!r} has no numeric year") from exc
        identifier = slugify(key)
        if identifier in seen:
            raise ValidationError(f"duplicate BibTeX citation key after normalization: {key}")
        seen.add(identifier)
        authors = [
            re.sub(r"\s+", " ", author).strip()
            for author in re.split(r"\s+and\s+", fields.get("author", "Unknown"))
        ]
        papers.append(
            {
                "id": identifier,
                "title": title,
                "authors": authors,
                "year": year,
                "venue": fields.get("journal", fields.get("booktitle", "")),
                "doi": fields.get("doi", ""),
                "url": fields.get("url", ""),
                "abstract": fields.get("abstract", ""),
                "notes": f"Imported from BibTeX entry type {entry_type}.",
                "tags": [],
                "source_key": key,
            }
        )
    return papers


def load_bibtex(path: str | Path) -> list[dict[str, Any]]:
    """Read and parse a UTF-8 BibTeX file."""
    return parse_bibtex(Path(path).read_text(encoding="utf-8"))


def parse_csl_json(text: str) -> list[dict[str, Any]]:
    """Parse CSL JSON records using the portable subset needed for review work."""
    try:
        source = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid CSL JSON: {exc}") from exc
    if isinstance(source, dict):
        source = [source]
    if not isinstance(source, list):
        raise ValidationError("CSL JSON must be an object or list")
    papers: list[dict[str, Any]] = []
    for index, item in enumerate(source):
        if not isinstance(item, dict):
            raise ValidationError(f"CSL item {index} must be an object")
        title = str(item.get("title", "")).strip()
        if not title:
            raise ValidationError(f"CSL item {index} is missing title")
        issued = item.get("issued", {}).get("date-parts", [[]])
        try:
            year = int(issued[0][0])
        except (IndexError, TypeError, ValueError) as exc:
            raise ValidationError(f"CSL item {index} is missing an issued year") from exc
        authors = []
        for author in item.get("author", []):
            if "literal" in author:
                authors.append(str(author["literal"]))
            else:
                authors.append(
                    " ".join(
                        part
                        for part in (str(author.get("given", "")), str(author.get("family", "")))
                        if part
                    )
                )
        papers.append(
            {
                "id": slugify(str(item.get("id") or title)),
                "title": title,
                "authors": authors or ["Unknown"],
                "year": year,
                "venue": str(item.get("container-title", "")),
                "doi": str(item.get("DOI", "")),
                "url": str(item.get("URL", "")),
                "abstract": str(item.get("abstract", "")),
                "notes": "Imported from CSL JSON.",
                "tags": [],
            }
        )
    return papers


def load_csl_json(path: str | Path) -> list[dict[str, Any]]:
    """Read and parse UTF-8 CSL JSON."""
    return parse_csl_json(Path(path).read_text(encoding="utf-8"))
